"""Publica o dashboard num Hugging Face Space (Streamlit SDK) — URL pública SEM o
handshake de login do Streamlit Cloud (abre para qualquer pessoa/ferramenta).

Pré-requisito: o usuário já fez `hf auth login` (token fica só na máquina dele).
Uso: py -3 src/deploy_hf.py
"""
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, whoami

SPACE_NAME = "hidreletricas-iat"
ROOT = Path(__file__).resolve().parent.parent

# Arquivos que o app precisa rodar na nuvem (mesmo conjunto do deploy GitHub)
INCLUDE = [
    "requirements.txt",
    "config.yaml",
    ".streamlit/config.toml",
    "dashboard/app.py",
    "dashboard/utils.py",
    "data/bacias_parana.geojson",
    "data/processed/processos_hidreletricas.csv",
    "data/processed/resumo_indicadores.json",
    "data/processed/metadados_execucao.json",
    "data/processed/erros_validacao.csv",
]
INCLUDE_GLOBS = ["dashboard/assets/*.png", "dashboard/assets/*.qgs"]

_README = """---
title: Central de Projetos Hidrelétricos do Paraná
emoji: 💧
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.58.0
app_file: dashboard/app.py
pinned: false
license: mit
---

# Central de Projetos Hidrelétricos do Estado do Paraná — IAT/PR

Dashboard institucional de acompanhamento dos processos de licenciamento ambiental de
empreendimentos hidrelétricos no Paraná (Instituto Água e Terra). Acesso público.
"""


def main():
    user = whoami()["name"]
    repo_id = f"{user}/{SPACE_NAME}"
    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="streamlit", exist_ok=True)
    print("Space:", repo_id)

    stage = Path(tempfile.mkdtemp(prefix="hfspace_"))
    (stage / "README.md").write_text(_README, encoding="utf-8")
    files = list(INCLUDE)
    for g in INCLUDE_GLOBS:
        files += [str(p.relative_to(ROOT)).replace("\\", "/") for p in ROOT.glob(g)]
    for rel in files:
        src = ROOT / rel
        if not src.exists():
            print("  (faltou)", rel)
            continue
        dst = stage / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print("arquivos no staging:", sum(1 for _ in stage.rglob("*") if _.is_file()))

    api.upload_folder(repo_id=repo_id, repo_type="space", folder_path=str(stage),
                      commit_message="Deploy dashboard hidreletricas IAT")
    shutil.rmtree(stage, ignore_errors=True)
    print("OK! URL publica (sem login):")
    print(f"  https://huggingface.co/spaces/{repo_id}")
    print(f"  https://{user.lower().replace('_','-')}-{SPACE_NAME}.hf.space")


if __name__ == "__main__":
    main()
