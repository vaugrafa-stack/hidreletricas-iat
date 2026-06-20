# 🚀 Publicar o dashboard na internet (link compartilhável)

Guia para colocar o painel no ar com um **link público permanente** (ex.: `https://hidreletricas-iat.streamlit.app`)
usando o **Streamlit Community Cloud** (gratuito). Qualquer pessoa abre no navegador, no PC ou celular.

> ✅ O projeto já está **pronto para deploy** (requirements enxuto, dados necessários versionados, botões adaptados
> para a nuvem). Basta seguir os passos abaixo.

---

## Passo 1 — Criar conta no GitHub (grátis, 2 min)
1. Acesse <https://github.com/join> e crie uma conta (guarde o usuário e a senha).
2. Confirme o e-mail.

## Passo 2 — Subir o projeto para o GitHub
**Opção A — GitHub Desktop (mais fácil, sem linha de comando):**
1. Baixe e instale o **GitHub Desktop**: <https://desktop.github.com>.
2. Abra, faça login com sua conta.
3. **File → Add Local Repository** → selecione a pasta `C:\Users\rafae\Downloads\IAT\Dashboard`.
   - Se ele disser que não é um repositório, clique em **"create a repository"** (eu já deixei um `.gitignore` pronto).
4. Em **Publish repository**: nome `hidreletricas-iat` (ou outro), **desmarque** "Keep this code private" se
   quiser que seja público (o repositório pode ser público; isso é separado do link do app). Clique **Publish**.

**Opção B — Linha de comando (se preferir):**
```bash
cd "C:\Users\rafae\Downloads\IAT\Dashboard"
git init                # (já feito, se eu rodei pra você)
git add .
git commit -m "Dashboard hidrelétricas IAT"
# crie um repositório vazio em github.com (botão New) e copie a URL, então:
git remote add origin https://github.com/SEU_USUARIO/hidreletricas-iat.git
git branch -M main
git push -u origin main
```

## Passo 3 — Publicar no Streamlit Community Cloud
1. Acesse <https://share.streamlit.io> e clique em **"Continue with GitHub"** (autorize o acesso).
2. Clique em **"Create app"** → **"Deploy a public app from GitHub"**.
3. Preencha:
   - **Repository:** `SEU_USUARIO/hidreletricas-iat`
   - **Branch:** `main`
   - **Main file path:** `dashboard/app.py`
   - **App URL:** escolha o final do link (ex.: `hidreletricas-iat`).
4. Clique em **Deploy**. A primeira vez leva ~2-5 min (instala as bibliotecas).
5. Pronto! Copie o link (ex.: `https://hidreletricas-iat.streamlit.app`) e compartilhe. 🎉

---

## 🔄 Como atualizar os dados depois
O app na nuvem lê os dados versionados no GitHub. Quando a planilha mudar:
1. Rode o pipeline localmente: `python src/run_pipeline.py`
2. Suba a atualização (GitHub Desktop: **Commit** → **Push**; ou `git add . && git commit -m "atualiza dados" && git push`).
3. O Streamlit Cloud **redeploya sozinho** em ~1 min.

## ℹ️ Coisas importantes
- **Botões de abrir:** na nuvem, **🌐 Google Earth Web** e **📍 Google Maps** abrem no navegador de quem acessa.
  Os botões de **QGIS** e **Google Earth Desktop** aparecem **só na versão local** (eles abrem programas instalados
  na máquina, o que não faz sentido para um visitante remoto). Isso é automático (variável `IAT_PUBLIC`).
- **Dados públicos:** o link é aberto — qualquer um vê os 1.598 processos. Se um dia quiser proteger, dá para
  adicionar uma senha (peça que eu configuro via `st.secrets`).
- **Camadas do IAT (GeoPR):** funcionam normalmente na nuvem (carregam no navegador do visitante).
- **`requirements.txt`** é o do dashboard (enxuto). As libs do pipeline ficam em `requirements-pipeline.txt`
  e **não** são instaladas na nuvem (de propósito — `arcgis` é pesado demais).
