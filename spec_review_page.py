"""Local page: review a business spec with the po-spec-review skill (via Claude Code),
download the stories PDF and push stories and tasks to Azure DevOps.

Run: python -m streamlit run spec_review_page.py
Uses the Claude Code login (subscription); no API key. Local use only.
"""
import streamlit as st

from src import azure_devops, claude_cli

STYLE = """
<style>
.block-container {max-width: 1000px; padding-top: 2.5rem;}
h1 {font-weight: 800; letter-spacing: -0.02em;
    background: linear-gradient(90deg, #6D4AFF, #B04AFF);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
div[data-testid="stTextArea"] textarea {border-radius: 12px;}
div.stButton > button, div.stDownloadButton > button {border-radius: 10px; font-weight: 600;}
div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #6D4AFF, #8E4AFF); border: 0; padding: 0.6rem 1.6rem;
    box-shadow: 0 4px 14px rgba(109, 74, 255, 0.35);}
div[data-testid="stExpander"] {border-radius: 12px; border: 1px solid #E4E0F5; background: #FFFFFF;}
</style>
"""

MESSAGES = {
    "not_found": "Claude Code não encontrado. Instale-o ou confira se existe em "
                 "`C:\\Users\\<você>\\.local\\bin\\claude.exe`.",
    "auth": "O login do Claude Code expirou. Abra um terminal, rode `claude` e entre de novo; depois tente outra vez.",
}
STATUS = {"new": "novo", "sent": "já enviado", "partial": "parcial"}


def _scope(org: str, project: str) -> tuple[str, str]:
    try:
        return azure_devops.normalize_organization(org), project.strip()
    except ValueError:
        return "", ""


def run_review(data: bytes, filename: str) -> None:
    ss = st.session_state
    ss.pop("review", None)
    ss.pop("azdo_prev", None)
    with st.status("Revisando com o Claude Code (pode levar alguns minutos)...", expanded=True) as status:
        box = st.empty()
        seen: list[str] = []

        def on_event(event: claude_cli.Event) -> None:
            if event.kind == "text":
                seen.append(event.text)
                box.markdown(seen[-1])

        try:
            ss["review"] = claude_cli.review_spec(data, filename, on_event=on_event)
            status.update(label="Revisão concluída", state="complete", expanded=False)
        except claude_cli.ClaudeCliError as err:
            status.update(label="A revisão falhou", state="error")
            st.error(MESSAGES.get(err.kind, str(err)))


def render_review(review: claude_cli.ReviewResult) -> None:
    st.subheader("Resultado da revisão")
    st.markdown(review.text)
    st.download_button("Baixar PDF das histórias", review.pdf, "historias.pdf", "application/pdf",
                       key="dl_pdf")


def render_azure(review: claude_cli.ReviewResult) -> None:
    ss = st.session_state
    st.subheader("Enviar ao Azure DevOps")
    st.caption("Só histórias e tasks. Primeiro veja a prévia; o envio só acontece no botão de confirmar. "
               "Teste antes num projeto de sandbox. O token fica só nesta sessão.")
    try:
        items = azure_devops.items_from_stories_json(review.stories)
    except (ValueError, KeyError, TypeError) as err:
        st.error(f"As histórias geradas não puderam ser lidas: {err}")
        return
    org = st.text_input("Organização", key="azdo_org")
    project = st.text_input("Projeto", key="azdo_project")
    token = st.text_input("Token (PAT)", type="password", key="azdo_pat")
    scope = _scope(org, project)
    fingerprint = repr(review.stories)
    ledgers = ss.setdefault("azdo_ledgers", {})
    ledger = ledgers.setdefault(scope, azure_devops.Ledger.load(None, *scope))

    if st.button("Ver prévia (não envia nada)", key="azdo_preview"):
        ss["azdo_prev"] = (scope, fingerprint)
    previewed = ss.get("azdo_prev") == (scope, fingerprint) and all(scope)
    if previewed:
        lines = []
        for line in azure_devops.plan(items, ledger):
            lines.append(f"- **[{STATUS.get(line.status, line.status)}]** {line.story_title}")
            lines += [f"    - {title}" for title in line.task_titles]
            if line.warning:
                lines.append(f"    - ⚠ {line.warning}")
        st.markdown("\n".join(lines))

    if st.button("Confirmar e enviar ao Azure", key="azdo_confirm", type="primary", disabled=not previewed):
        if not token.strip():
            st.error("Informe o token (PAT) para enviar.")
            return
        try:
            client = azure_devops.AzureDevOpsClient(org, project, token)
            report = azure_devops.push(client, items, ledger, confirmed=True)
        except ValueError as err:
            st.error(str(err))
            return
        st.success(f"{report.created_stories} histórias e {report.created_tasks} tasks criadas "
                   f"({report.skipped} já existiam).")
        for url in report.urls:
            st.markdown(f"- {url}")
        if report.error:
            st.error(str(report.error))


def main() -> None:
    st.set_page_config(page_title="Revisão de especificação", page_icon="📋", layout="wide")
    st.markdown(STYLE, unsafe_allow_html=True)
    st.title("Revisão de especificação")
    st.write("Envie a especificação, receba a revisão (`po-spec-review`), o PDF das histórias com tasks "
             "e, se quiser, suba para o Azure DevOps. Roda pelo seu login do Claude Code, sem chave de API.")
    st.caption("O documento vai para o Claude, como quando você o anexa no chat, e fica só numa pasta "
               "temporária apagada ao final. Uso local.")

    upload = st.file_uploader("Especificação (PDF, TXT ou MD)", type=["pdf", "txt", "md"], key="spec_file")
    text = st.text_area("...ou cole o texto da especificação", key="spec_text", height=160)
    if st.button("Revisar", key="run_review", type="primary"):
        if upload is not None:
            run_review(upload.getvalue(), upload.name)
        elif text.strip():
            run_review(text.encode("utf-8"), "spec.txt")
        else:
            st.error("Envie um arquivo ou cole o texto da especificação.")

    review = st.session_state.get("review")
    if review is not None:
        render_review(review)
        render_azure(review)


main()
