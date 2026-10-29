"""Télécharge le dataset figshare de Jun Cheng (CC BY 4.0) et vérifie chaque fichier.

Source : https://figshare.com/articles/dataset/brain_tumor_dataset/1512427
Les sommes MD5 attendues sont celles publiées par l'API figshare. Un fichier dont la
somme ne correspond pas est supprimé, et le script s'arrête en erreur.

    python experiments/brain_mri/download_figshare.py [dossier]   # défaut : data/figshare
"""

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ARTICLE_ID = 1512427
API = f"https://api.figshare.com/v2/articles/{ARTICLE_ID}"


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(API, timeout=60) as response:
        article = json.load(response)
    (out_dir / "article.json").write_text(json.dumps(article, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{article['title']} — version {article['version']} — licence {article['license']['name']}")

    for f in article["files"]:
        target = out_dir / f["name"]
        if target.exists() and md5(target) == f["computed_md5"]:
            print(f"déjà présent, MD5 vérifié : {f['name']}")
            continue
        print(f"téléchargement : {f['name']} ({f['size'] / 1e6:.0f} Mo)", flush=True)
        tmp = target.with_suffix(target.suffix + ".part")
        urllib.request.urlretrieve(f["download_url"], tmp)
        actual = md5(tmp)
        if actual != f["computed_md5"]:
            tmp.unlink()
            sys.exit(f"MD5 incorrect pour {f['name']} : {actual} au lieu de {f['computed_md5']}")
        tmp.replace(target)
        print(f"  MD5 vérifié : {actual}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/figshare"))
