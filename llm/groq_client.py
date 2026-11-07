import json
import time
from groq import Groq
from core.config import Config

client = Groq(api_key=Config.GROQ_API_KEY)


## asks Groq to pick one label for the text
## returns {"label": ..., "confidence": ..., "model": ...}
## returns None if it fails after 3 tries
def prelabel(text, labels):
    prompt = (
        "Classify the text into exactly one of these labels: " + ", ".join(labels) + ".\n"
        'Reply only with JSON like {"label": "...", "confidence": 0.0 to 1.0}.\n\n'
        "Text: " + text
    )

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            data = json.loads(response.choices[0].message.content)

            ## the label must be one of ours
            if data.get("label") not in labels:
                return None

            confidence = float(data.get("confidence", 0))
            confidence = max(0.0, min(1.0, confidence))
            return {"label": data["label"], "confidence": confidence, "model": Config.GROQ_MODEL}

        except Exception as e:
            print("Groq error:", e)
            ## wait longer after each failure (2s, 4s, 6s)
            time.sleep(2 * (attempt + 1))

    return None