import feedparser
import pandas as pd

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

print(df.head())

## continuar con la limpieza de datos, análisis o visualización según sea necesario.