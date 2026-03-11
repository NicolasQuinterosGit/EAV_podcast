import feedparser
import pandas as pd
import re
import unicodedata

# region Carga de datos
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


# region Carga CSV de métricas de Spotify
metrics_df = pd.read_csv(
    "spotify_metrics.csv",
    encoding="utf-8-sig",
    sep=";"
)

#print(metrics_df.head())
#print(metrics_df.columns)
# endregion
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
metrics_df["Date"] = pd.to_datetime(metrics_df["Date"], errors="coerce", dayfirst=True)
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
# endregion

# region Merge de DataFrames
merged_df = pd.merge(
    df,
    metrics_df,
    on="title_clean",
    how="inner"
)
print("Episodios combinados:", len(merged_df))

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

# region Analisis básico


# region Duración promedio de los episodios

bins = [0, 15, 20, 25, 30, 60]
labels = ["0-15", "15-20", "20-25", "25-30", "30+"]

merged_df["duration_group"] = pd.cut(
    merged_df["duration_minutes"],
    bins=bins,
    labels=labels
)

group_analysis = merged_df.groupby("duration_group", observed=False)[
    "Total_Reproducciones_y_descargas"
].mean()

# endregion
# region Normalizacion de antiguedad
merged_df["days_since_publish"] = (
    pd.Timestamp.today() - merged_df["published"]
).dt.days

merged_df["plays_per_day"] = (
    merged_df["Total_Reproducciones_y_descargas"] /
    merged_df["days_since_publish"]
)

top_recent = merged_df.sort_values(
    by="plays_per_day",
    ascending=False
).head(5)

print(top_recent[[
    "title",
    "plays_per_day",
    "duration_minutes"
]])
# endregion
# region Promedio de  días entre episodios
df["days_between"] = df["published"].diff().dt.days.abs()
#print("Promedio de días entre episodios:", df["days_between"].mean())
# endregion
# endregion

# Region Análisis de titulos

# region Los titulos con preguntas tienen mejor rendimiento?
merged_df["is_question"] = merged_df["title"].str.contains(r"\?")
question_analysis = merged_df.groupby("is_question")[
    "Total_Reproducciones_y_descargas"
].mean()

print(question_analysis)
# endregion

# region invitados aumentan reproducciones?
merged_df["has_guest"] = merged_df["title"].str.contains(
    r"ft\.|feat|featuring",
    case=False,
    regex=True
)

guest_analysis = merged_df.groupby("has_guest")[
    "Total_Reproducciones_y_descargas"
].mean()

print(guest_analysis)
# endregion

# region titulos largos vs cortos
merged_df["title_length"] = merged_df["title"].str.len()

title_length_corr = merged_df["title_length"].corr(
    merged_df["Total_Reproducciones_y_descargas"]
)

print("Correlación longitud del título vs reproducciones(+ = largos mejor/ - = cortos mejor ):", title_length_corr)
# endregion

# region palabras clave en títulos

top_episodes = merged_df.sort_values(
    by="plays_per_day",
    ascending=False
).head(20)
from collections import Counter

words = []

for title in top_episodes["title"]:
    words.extend(title.lower().split())

word_counts = Counter(words)

print(word_counts.most_common(15))
# endregion

# -------------------
# INTERPRETACION INSIGHTS
# -------------------

question_diff = question_analysis[True] - question_analysis[False]

if question_diff > 0:
    question_insight = "Los títulos con preguntas generan más reproducciones."
else:
    question_insight = "Los títulos descriptivos funcionan mejor que las preguntas."


guest_diff = guest_analysis[True] - guest_analysis[False]

if guest_diff > 0:
    guest_insight = "Los episodios con invitados generan más reproducciones."
else:
    guest_insight = "Los episodios sin invitados generan más reproducciones."


if title_length_corr > 0:
    title_length_insight = "Los títulos más largos tienden a funcionar mejor."
else:
    title_length_insight = "Los títulos más cortos tienden a funcionar mejor."


top_words = ", ".join([word for word, count in word_counts.most_common(10)])
# endregion

# region Reporte final
total_episodes = len(merged_df)

avg_duration = merged_df["duration_minutes"].mean()

merged_df = merged_df.sort_values("published")

merged_df["days_between"] = merged_df["published"].diff().dt.days

avg_frequency = merged_df["days_between"].dropna().mean()

best_duration_group = group_analysis.idxmax()
best_duration_value = group_analysis.max()

best_episode = merged_df.sort_values(
    by="plays_per_day",
    ascending=False
).iloc[0]
print("\n----- Reporte del análisis de podcasts -----\n")

print(f"Total episodios analizados: {total_episodes}")

print(f"Duración promedio: {avg_duration:.2f} minutos")

print(f"Frecuencia promedio de publicación: {avg_frequency:.2f} días\n")

print(f"Rango de duración con mejor rendimiento: {best_duration_group} min")
print(f"Promedio de reproducciones en ese rango: {best_duration_value:.0f}\n")

print("Episodio con mejor rendimiento diario:")

print(best_episode["title"])
print(f"{best_episode['plays_per_day']:.2f} reproducciones por día")
print(f"Duración: {best_episode['duration_minutes']:.2f} minutos")
print("\n----- FIN DEL REPORTE -----\n")


# region Guardado de reporte en archivo de texto

report = f"""
Reporte del análisis de podcasts

Total episodios: {total_episodes}

Duración promedio: {avg_duration:.2f} minutos
Frecuencia promedio: {avg_frequency:.2f} días

Mejor rango de duración: {best_duration_group}
Promedio reproducciones: {best_duration_value:.0f}

Mejor episodio por rendimiento diario:
{best_episode['title']}

Plays por día: {best_episode['plays_per_day']:.2f}
Duración: {best_episode['duration_minutes']:.2f}

INSIGHTS DE TITULOS

Preguntas vs descriptivos:
{question_insight}

Invitados:
{guest_insight}

Longitud de título:
{title_length_insight}

Palabras frecuentes en episodios exitosos:
{top_words}
"""

with open("podcast_report.txt", "w", encoding="utf-8") as f:
    f.write(report)

# endregion
# endregion