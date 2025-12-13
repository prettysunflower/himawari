import requests
import json
from datetime import datetime
import hashlib
import re
from tqdm import tqdm
from nacl.hash import blake2b
import nacl.encoding
import time
import subprocess
import smtplib
from email.message import EmailMessage
from email.utils import format_datetime
import dateutil.parser
import glob
import os

s = smtplib.SMTP(os.environ["SMTP_HOST"], port=int(os.environ["SMTP_PORT"]))
s.starttls()
s.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])

cache_file_path = os.path.join(os.environ["CACHE_FOLDER"], "pixiv_notifs.cache")

try:
    with open(cache_file_path) as cache_file:
        cache = json.loads(cache_file.read())
except FileNotFoundError:
    cache = {"image_ids": []}


def save_cache():
    with open(cache_file_path, "w") as cache_file:
        cache_file.write(json.dumps(cache, ensure_ascii=False))


def pixiv_login():
    if (
        "access_token" in cache
        and int(datetime.utcnow().timestamp()) < cache["access_token_expiration"]
    ):
        return cache["access_token"]

    print("Requesting Pixiv access token")
    request_date = datetime.utcnow()
    request_date_text = request_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    response = requests.post(
        url="https://oauth.secure.pixiv.net/auth/token",
        headers={
            "X-Client-Time": request_date_text,
            "X-Client-Hash": hashlib.md5(
                (
                    request_date_text
                    + "28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c"
                ).encode()
            ).hexdigest(),
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        },
        # The following comes from the Pixiv App API on gallery-dl
        # (https://github.com/mikf/gallery-dl/blob/f1aa3af11939f77b03bb0fcab2744dc7f98f8dde/gallery_dl/extractor/pixiv.py#L1096)
        data={
            "client_id": "MOBrBDS8blbauoSck0ZfDbtuzpyT",
            "client_secret": "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj",
            "grant_type": "refresh_token",
            "refresh_token": os.environ["PIXIV_REFRESH_TOKEN"],
            "get_secure_url": "1",
        },
    )

    access_token = response.json()["access_token"]
    cache["access_token"] = access_token
    cache["access_token_expiration"] = int(request_date.timestamp()) + 3600
    save_cache()

    return access_token


access_token = pixiv_login()

response = requests.get(
    url="https://app-api.pixiv.net/v2/illust/follow",
    params={
        "restrict": "all",
    },
    headers={
        "Authorization": f"Bearer {access_token}",
    },
).json()

for x in response["illusts"]:
    user_id_hashed = blake2b(
        str(x["user"]["id"]).encode(), encoder=nacl.encoding.HexEncoder
    ).decode()

    if x["id"] in cache["image_ids"]:
        continue

    print(f"Downloading artwork {x['id']}")

    subprocess.run(
        [
            ".venv/bin/gallery-dl", "-d", os.environ["GALLERY_DL_FOLDER"], "--write-metadata", "-o", "refresh-token=" + os.environ["PIXIV_REFRESH_TOKEN"], f"https://pixiv.net/artworks/{x['id']}"
        ]
    )
    
    msg = EmailMessage()
    msg[
        "Subject"
    ] = f"New illustration by {x['user']['name']} (@{x['user']['account']})"
    msg["From"] = os.environ["FROM_EMAIL"]
    msg["To"] = os.environ["TO_EMAIL"]
    msg.set_content(f"{x['title']}\n-----\n{x['caption']}\n-----\nhttps://www.pixiv.net/en/artworks/{x['id']}")
    msg.add_header("Date", format_datetime(dateutil.parser.isoparse(x["create_date"])))
    pages = []

    if "meta_single_page" in x and x["meta_single_page"]:
        filename = (
            x["meta_single_page"]["original_image_url"].split("/")[-1].split("?")[0]
        )
        pages.append(
            os.path.join(os.environ["GALLERY_DL_FOLDER"], f"pixiv/{x['user']['id']} {x['user']['account']}/{filename}")
        )
    else:
        for image in x["meta_pages"]:
            filename = image["image_urls"]["original"].split("/")[-1].split("?")[0]
            pages.append(
                os.path.join(os.environ["GALLERY_DL_FOLDER"], f"pixiv/{x['user']['id']} {x['user']['account']}/{filename}")
            )

    for page in pages:
        try:
            with open(page, "rb") as file:
                image_data = file.read()
        except FileNotFoundError:
            continue
        subtype = page.split(".")[-1]
        msg.add_attachment(
            image_data, maintype="image", subtype=subtype, filename=page
        )

    try:
        s.send_message(msg)
    except smtplib.SMTPSenderRefused as e:
        if e.args[0] == 552:
            msg = EmailMessage()
            msg[
                "Subject"
            ] = f"New illustration by {x['user']['name']} (@{x['user']['account']})"
            msg["From"] = os.environ["FROM_EMAIL"]
            msg["To"] = os.environ["TO_EMAIL"]
            msg.set_content(f"{x['title']}\n-----\n{x['caption']}\n-----\nhttps://www.pixiv.net/en/artworks/{x['id']}")
            msg.add_header("Date", format_datetime(dateutil.parser.isoparse(x["create_date"])))
            s.send_message(msg)
        else:
            raise e


    cache["image_ids"].append(x["id"])
    save_cache()

s.quit()
