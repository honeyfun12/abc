from flask import Flask, render_template, request, jsonify
from fetchers import springfield, subslikescript

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/script", methods=["POST"])
def get_script():
    data = request.get_json(force=True)
    show = (data.get("show") or "").strip()
    season = data.get("season", "1")
    episode = (data.get("episode") or "").strip()

    if not show or not episode:
        return jsonify({"error": "드라마 제목과 에피소드를 입력해 주세요."}), 400

    try:
        season_int = int(season)
    except (TypeError, ValueError):
        return jsonify({"error": "시즌은 숫자로 입력해 주세요."}), 400

    # Try Springfield Springfield first
    result = springfield.fetch_script(show, season_int, episode)

    # Fall back to SubsLikeScript if nothing found
    if result["error"] or not result["script"]:
        fallback = subslikescript.fetch_script(show, season_int, episode)
        if fallback["script"]:
            result = fallback
        elif not result["script"]:
            # Return whichever has an error message
            result["error"] = (
                result["error"]
                or fallback["error"]
                or "스크립트를 찾을 수 없습니다."
            )

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
