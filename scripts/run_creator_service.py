import sys
from pathlib import Path

import uvicorn


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


if __name__ == "__main__":
    uvicorn.run("media_login.creator_gateway:app", host="127.0.0.1", port=8000)
