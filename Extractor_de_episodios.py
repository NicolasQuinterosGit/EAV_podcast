import feedparser
import pandas as pd
import re
import unicodedata

# region -Extracción de episodios del RSS-
#Lee el RSS del podcast
RSS_URL = "https://anchor.fm/s/f9acaa04/podcast/rss"

feed = feedparser.parse(RSS_URL)

#Extrae la información de cada episodio
episodes = []

for entry in feed.entries:
    title = entry.get("title","")
    descprition = entry.get("description","")
    published = entry.get("published","")

    duration = entry.get("itunes_duration", None)

    episodes.append({
        "title": title,
        "description": descprition,
        "published": published,
        "duration": duration
    })
#Pasar a DataFrame
df = pd.DataFrame(episodes)

#Guardar en CSV
df.to_csv("podcast_episodes.csv", index=False)
print("Los episodios del podcast se guardaron en podcast_episodes.csv")

print(df)

# region normalizar la duración a minutos

def convert_to_minutes(duration):
    if duration is None:
        return None
    
    if ":" in duration:
        parts = duration.split(":")
        parts = [int(p) for p in parts]
        
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return hours * 60 + minutes + seconds / 60
        elif len(parts) == 2:
            minutes, seconds = parts
            return minutes + seconds / 60
    
    if duration.isdigit():
        return int(duration) / 60
    
    return None

df["duration_minutes"] = df["duration"].apply(convert_to_minutes)

# region Conversión de la fecha de publicación a formato datetime
df["published"] = pd.to_datetime(df["published"], errors="coerce")
df = df.sort_values(by="published", ascending=False)
# endregion
# endregion
# endregion

# region Carga CSV de métricas de Spotify
metrics_df = pd.read_csv(
    "spotify_metrics.csv",
    encoding="utf-8-sig",
    sep=";"
)

#print(metrics_df.head())
#print(metrics_df.columns)
# endregion

# region -Limpieza de columnas-
# region Normalización de titulos para hacer merge
def clean_title(text):
    text = text.lower().strip()
    
    # Quitar acentos
    text = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    
    # Eliminar patrones tipo s02, ep 19, s2 x ep 19, etc
    text = re.sub(r's\d+\s*x?\s*ep?\s*\d+', '', text)
    text = re.sub(r'ep?\s*\d+', '', text)
    text = re.sub(r's\d+', '', text)
    
    # Eliminar nombre del podcast si aparece
    text = text.replace("espanol al vuelo", "")
    
    # Quitar caracteres especiales
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Quitar espacios múltiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

df["title_clean"] = df["title"].apply(clean_title)
metrics_df["title_clean"] = metrics_df["Title"].apply(clean_title)
# endregion
# region Conversor de fechas
metrics_df["Date"] = pd.to_datetime(metrics_df["Date"], errors="coerce")
# endregion
# region Convierte reproducciones y descargas a números
metrics_df["Total_Reproducciones_y_descargas"] = (
    metrics_df["Total_Reproducciones_y_descargas"]
    .astype(str)
    .str.replace(",", "")
    .astype(float)
)

metrics_df["Reproducciones_Spotify"] = (
    metrics_df["Reproducciones_Spotify"]
    .astype(str)
    .str.replace(",", "")
    .astype(float)
)
# endregion
# region Filtrado por status "Published"
#metrics_df = metrics_df[metrics_df["Status"] == "Published"]
# endregion
# region Merge de DataFrames
merged_df = pd.merge(
    df,
    metrics_df,
    on="title_clean",
    how="inner"
)
print("Episodios combinados:", len(merged_df))
# endregion
# region Debugging del merge

    # No se mergearon todos los episodios. Voy a comparar para ver por qué

    # rss_titles = set(df["title_clean"])
    # csv_titles = set(metrics_df["title_clean"])

    # missing_in_csv = rss_titles - csv_titles
    # missing_in_rss = csv_titles - rss_titles

    # print("En RSS pero NO en CSV:", len(missing_in_csv))
    # print("En CSV pero NO en RSS:", len(missing_in_rss))

    # print(list(missing_in_csv)[:10])
    # print(list(missing_in_rss)[:10])

    # print(metrics_df.columns)
# endregion
# endregion

#region -Insights-
print("Insights:")

# region Duración promedio de los episodios
print("Duración promedio:", df["duration_minutes"].mean())
# endregion
# region Promedio de  días entre episodios
df["days_between"] = df["published"].diff().dt.days.abs()
print("Promedio de días entre episodios:", df["days_between"].mean())
# endregion
# endregion