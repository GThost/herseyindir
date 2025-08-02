# Gerekli kütüphaneleri içe aktarın
import os
import re
import uuid
import requests
from flask import Flask, request, jsonify, send_file
import yt_dlp
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# İndirme klasörünü belirleyin
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return "✅ Herseyindir.com Video API aktif!"

@app.route("/indir", methods=["POST"])
def indir():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "Lütfen geçerli bir URL girin."}), 400

    output_path = None
    try:
        # Eğer direkt mp4 bağlantısı geldiyse (SnapInsta tokenlı)
        if video_url.endswith(".mp4") or "snapcdn" in video_url or "token=" in video_url:
            filename = f"{uuid.uuid4()}.mp4"
            output_path = os.path.join(DOWNLOAD_FOLDER, filename)

            response = requests.get(video_url, stream=True)
            if response.status_code != 200:
                return jsonify({"error": f"Video alınamadı. Durum: {response.status_code}"}), 400

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"✅ SnapInsta .mp4 linki indirildi: {filename}")
            return send_file(output_path, as_attachment=True, download_name=filename)

        # Diğer tüm linkler için (örn. YouTube, Instagram normal link)
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get("title", str(uuid.uuid4()))
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
            filename = f"{safe_title}.mp4"
            output_path = os.path.join(DOWNLOAD_FOLDER, filename)

        print(f"▶️ Video indiriliyor: {title}")

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': output_path,
            'quiet': True,
            'nocheckcertificate': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        if not os.path.exists(output_path):
            return jsonify({"error": "İndirme başarısız. Dosya oluşturulamadı."}), 500

        print(f"✅ İndirme tamamlandı: {output_path}")
        return send_file(output_path, as_attachment=True, download_name=filename)

    except yt_dlp.utils.DownloadError as e:
        print(f"❌ yt-dlp hatası: {e}")
        return jsonify({"error": f"İndirme hatası: {str(e)}"}), 500
    except Exception as e:
        print(f"❌ Genel hata: {e}")
        return jsonify({"error": f"Hata oluştu: {str(e)}"}), 500
    finally:
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
                print(f"🧹 Dosya silindi: {output_path}")
            except OSError as e:
                print(f"⚠️ Silme hatası: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
