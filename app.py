"""Streamlit UI: PRD & User Story Generator. UI only; logic lives in src/."""
import time

import pandas as pd
import streamlit as st

from src import azure_devops
from src.demo import DEMO_CASES, load_demo
from src.exporters import azure_devops_csv, jira_csv, prd_markdown
from src.models import PipelineResult
from src.pipeline import MAX_IDEA_CHARS, STEPS, PipelineError, run_pipeline
from src.providers import PROVIDERS, ProviderError, get_provider

DEMO_STEP_DELAY = 0.2

TEXT = {
    "en": {
        "title": "AI PRD & User Story Generator",
        "subtitle": "From a feature idea to a PRD, INVEST-reviewed user stories and Gherkin criteria, ready to import into Azure DevOps or Jira.",
        "language": "Output language", "demo": "Demo mode (no API key)", "provider": "Provider",
        "key": "API key", "model": "Model",
        "privacy": "Your idea is sent to the provider you choose. The key stays in this session only and is never stored.",
        "idea": "Describe the feature idea", "examples": "Try an example:", "generate": "Generate",
        "case": {"referral": "Referral program", "abandoned_cart": "Abandoned cart"},
        "steps": {"prd": "Writing the PRD", "stories": "Breaking it into user stories",
                  "invest": "Reviewing stories with INVEST", "gherkin": "Writing Gherkin acceptance criteria",
                  "tasks": "Writing the tasks"},
        "done": "Done", "failed": "Stopped at: {step}. What was already generated is shown below.",
        "demo_note": "Demo mode replays a pre-written example. Turn it off in the sidebar to use your own idea.",
        "no_key": "Enter an API key in the sidebar, or turn on demo mode.",
        "tabs": ["PRD", "Stories", "Gherkin", "Export"],
        "invest_before": "INVEST before (0-12)", "invest_after": "INVEST after (0-12)",
        "story": "Story", "review_notes": "Reviewer notes", "tasks": "Tasks",
        "dl_prd": "Download PRD (Markdown)", "dl_azure": "Download Azure DevOps CSV",
        "dl_jira": "Download Jira CSV",
        "import_help": "How to import: see docs/import-guide.md in the repository.",
        "azdo_title": "Link with Azure DevOps",
        "azdo_help": "Sends the stories and their tasks (no epics) to a project. The token stays in this session only and is never stored. Try a sandbox project first.",
        "azdo_org": "Organization (name or dev.azure.com URL)", "azdo_project": "Project",
        "azdo_pat": "Personal access token (Work Items: read and write)",
        "azdo_preview": "Preview", "azdo_send": "Send to Azure DevOps",
        "azdo_missing": "Fill in the organization, the project and the token.",
        "azdo_status": {"new": "new", "sent": "already sent", "partial": "partly sent"},
        "azdo_summary": "Created {stories} stories and {tasks} tasks; {skipped} skipped (already sent).",
    },
    "pt-BR": {
        "title": "Gerador de PRD e Histórias de Usuário com IA",
        "subtitle": "De uma ideia de funcionalidade a um PRD, histórias revisadas pelo INVEST e critérios em Gherkin, prontos para importar no Azure DevOps ou no Jira.",
        "language": "Idioma da saída", "demo": "Modo demo (sem chave de API)", "provider": "Provedor",
        "key": "Chave de API", "model": "Modelo",
        "privacy": "Sua ideia é enviada ao provedor escolhido. A chave fica só nesta sessão e nunca é armazenada.",
        "idea": "Descreva a ideia da funcionalidade", "examples": "Experimente um exemplo:", "generate": "Gerar",
        "case": {"referral": "Programa de indicação", "abandoned_cart": "Carrinho abandonado"},
        "steps": {"prd": "Escrevendo o PRD", "stories": "Quebrando em histórias de usuário",
                  "invest": "Revisando as histórias com INVEST", "gherkin": "Escrevendo critérios de aceite em Gherkin",
                  "tasks": "Escrevendo as tasks"},
        "done": "Pronto", "failed": "Parou em: {step}. O que já foi gerado aparece abaixo.",
        "demo_note": "O modo demo reproduz um exemplo pré-escrito. Desligue-o na barra lateral para usar sua própria ideia.",
        "no_key": "Informe uma chave de API na barra lateral ou ligue o modo demo.",
        "tabs": ["PRD", "Histórias", "Gherkin", "Exportar"],
        "invest_before": "INVEST antes (0-12)", "invest_after": "INVEST depois (0-12)",
        "story": "História", "review_notes": "Notas do revisor", "tasks": "Tasks",
        "dl_prd": "Baixar PRD (Markdown)", "dl_azure": "Baixar CSV do Azure DevOps",
        "dl_jira": "Baixar CSV do Jira",
        "import_help": "Como importar: veja docs/import-guide.pt-BR.md no repositório.",
        "azdo_title": "Link com Azure DevOps",
        "azdo_help": "Envia as histórias e suas tasks (sem épicos) para um projeto. O token fica só nesta sessão e nunca é armazenado. Teste primeiro em um projeto de sandbox.",
        "azdo_org": "Organização (nome ou URL dev.azure.com)", "azdo_project": "Projeto",
        "azdo_pat": "Token de acesso pessoal (Work Items: leitura e escrita)",
        "azdo_preview": "Ver prévia", "azdo_send": "Enviar ao Azure DevOps",
        "azdo_missing": "Preencha a organização, o projeto e o token.",
        "azdo_status": {"new": "novo", "sent": "já enviado", "partial": "enviado em parte"},
        "azdo_summary": "Criadas {stories} histórias e {tasks} tasks; {skipped} ignoradas (já enviadas).",
    },
}


def set_example(case_id: str) -> None:
    st.session_state["idea"] = DEMO_CASES[case_id][st.session_state["lang"]]


def render_results(result: PipelineResult, t: dict, key: str = "", downloads: bool = True) -> None:
    tabs = st.tabs(t["tabs"])
    with tabs[0]:
        if result.prd:
            st.markdown(result.prd.to_markdown(result.language))
    with tabs[1]:
        if result.stories:
            before = {r.story_id: r for r in result.reviews}
            rows = []
            for s in result.stories:
                rv = before.get(s.id)
                rows.append({
                    "ID": s.id, "Epic": s.epic, t["story"]: s.to_text(result.language),
                    "MoSCoW": s.priority, "Pts": s.points,
                    t["invest_before"]: rv.scores.total if rv else None,
                    t["invest_after"]: (rv.scores_after.total if rv.scores_after else rv.scores.total) if rv else None,
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            notes = [r for r in result.reviews if r.comment]
            if notes:
                with st.expander(t["review_notes"]):
                    for r in notes:
                        st.markdown(f"**{r.story_id}** ({r.verdict}): {r.comment}")
            for s in result.stories:
                if s.tasks:
                    with st.expander(f"{s.id} — {s.title} · {t['tasks']} ({len(s.tasks)})"):
                        st.markdown("\n".join(
                            f"- **{task.title}**" + (f": {task.description}" if task.description else "")
                            for task in s.tasks))
    with tabs[2]:
        for s in result.stories:
            if s.scenarios:
                st.markdown(f"**{s.id} — {s.title}**")
                header = "# language: pt\n" if result.language == "pt-BR" else ""
                body = "\n\n".join(sc.to_gherkin(result.language).removeprefix("# language: pt\n")
                                   for sc in s.scenarios)
                st.code(header + body, language="gherkin")
    with tabs[3]:
        if downloads:
            st.download_button(t["dl_prd"], prd_markdown(result), "prd.md", "text/markdown", key=f"dl_prd{key}")
            # BOM so Excel on Windows reads the accents as UTF-8. Jira's importer gets no BOM.
            st.download_button(t["dl_azure"], "﻿" + azure_devops_csv(result), "azure_devops.csv",
                               "text/csv", key=f"dl_azure{key}")
            st.download_button(t["dl_jira"], jira_csv(result), "jira.csv", "text/csv", key=f"dl_jira{key}")
            st.caption(t["import_help"])
            if not st.session_state.get("demo"):
                render_azure_push(result, t)


def render_azure_push(result: PipelineResult, t: dict) -> None:
    ss = st.session_state
    items = azure_devops.items_from_result(result)
    fingerprint = result.model_dump_json()
    with st.expander(t["azdo_title"]):
        st.caption(t["azdo_help"])
        org = st.text_input(t["azdo_org"], key="azdo_org")
        project = st.text_input(t["azdo_project"], key="azdo_project")
        token = st.text_input(t["azdo_pat"], type="password", key="azdo_pat")
        try:
            scope = (azure_devops.normalize_organization(org), project.strip())
        except ValueError:
            scope = ("", "")
        ledgers = ss.setdefault("azdo_ledgers", {})
        ledger = ledgers.setdefault(scope, azure_devops.Ledger.load(None, *scope))

        if st.button(t["azdo_preview"], key="azdo_preview"):
            ss["azdo_previewed"] = fingerprint
        if ss.get("azdo_previewed") == fingerprint:
            lines = []
            for line in azure_devops.plan(items, ledger):
                lines.append(f"- **[{t['azdo_status'][line.status]}]** {line.story_title}")
                lines += [f"    - {title}" for title in line.task_titles]
                if line.warning:
                    lines.append(f"    - ⚠ {line.warning}")
            st.markdown("\n".join(lines))

        sendable = ss.get("azdo_previewed") == fingerprint
        if st.button(t["azdo_send"], key="azdo_send", type="primary", disabled=not sendable):
            if not (org.strip() and project.strip() and token.strip()):
                st.error(t["azdo_missing"])
                return
            try:
                client = azure_devops.AzureDevOpsClient(org, project, token)
            except ValueError as err:
                st.error(str(err))
                return
            try:
                report = azure_devops.push(client, items, ledger, confirmed=True)
            except ValueError as err:
                st.error(str(err))
                return
            st.success(t["azdo_summary"].format(stories=report.created_stories, tasks=report.created_tasks,
                                                skipped=report.skipped))
            for url in report.urls:
                st.markdown(f"- {url}")
            if report.error:
                st.error(str(report.error))


def main() -> None:
    st.set_page_config(page_title="PRD & Story Generator", page_icon="📝", layout="wide")
    ss = st.session_state
    ss.setdefault("lang", "pt-BR")
    ss.setdefault("demo", True)
    ss.setdefault("idea", "")

    with st.sidebar:
        st.selectbox("Language / Idioma", ["pt-BR", "en"], key="lang",
                     format_func=lambda x: "Português (BR)" if x == "pt-BR" else "English")
        t = TEXT[ss["lang"]]
        st.toggle(t["demo"], key="demo")
        live = not ss["demo"]
        provider = st.selectbox(t["provider"], list(PROVIDERS), key="provider", disabled=not live)
        st.text_input(t["key"], type="password", key="api_key", disabled=not live)
        st.text_input(t["model"], value=PROVIDERS[provider], key=f"model_{provider}", disabled=not live)
        if live:
            st.caption(t["privacy"])

    t = TEXT[ss["lang"]]
    st.title(t["title"])
    st.write(t["subtitle"])

    st.write(t["examples"])
    cols = st.columns(len(DEMO_CASES))
    for col, case_id in zip(cols, DEMO_CASES):
        col.button(t["case"][case_id], key=f"ex_{case_id}", on_click=set_example, args=(case_id,))
    st.text_area(t["idea"], key="idea", height=120, max_chars=MAX_IDEA_CHARS)

    if st.button(t["generate"], type="primary", key="generate"):
        ss.pop("result", None)
        idea = ss["idea"]
        if ss["demo"]:
            case_id = next((c for c, v in DEMO_CASES.items() if idea.strip() == v[ss["lang"]]), None)
            if case_id is None:
                st.info(t["demo_note"])
                case_id = "referral"
            with st.status(t["steps"]["prd"], expanded=True) as status:
                for step in STEPS:
                    status.update(label=t["steps"][step])
                    time.sleep(DEMO_STEP_DELAY)
                status.update(label=t["done"], state="complete", expanded=False)
            ss["result"] = load_demo(case_id, ss["lang"])
        elif not ss.get("api_key", "").strip():
            st.error(t["no_key"])
        elif not idea.strip():
            st.error(t["idea"] + "?")
        else:
            try:
                provider_obj = get_provider(ss["provider"], ss["api_key"], ss.get(f"model_{ss['provider']}"))
                live_box = st.empty()
                with st.status(t["steps"]["prd"], expanded=True) as status:
                    def on_step(step: str, partial: PipelineResult) -> None:
                        ss["result"] = partial
                        with live_box.container():
                            render_results(partial, t, key=f"_{step}", downloads=False)
                        nxt = STEPS.index(step) + 1
                        status.update(label=t["steps"][STEPS[nxt]] if nxt < len(STEPS) else t["done"])

                    try:
                        ss["result"] = run_pipeline(idea, ss["lang"], provider_obj, on_step=on_step)
                        status.update(label=t["done"], state="complete", expanded=False)
                    except PipelineError as err:
                        ss["result"] = err.partial
                        status.update(label=str(err), state="error")
                        st.error(f"{err} — {t['failed'].format(step=t['steps'][err.step])}")
                live_box.empty()
            except (ValueError, ProviderError) as err:
                st.error(str(err))

    result = ss.get("result")
    if result is not None:
        render_results(result, t)


main()
