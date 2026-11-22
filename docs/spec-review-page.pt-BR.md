# Página de revisão de especificação (local)

Uma página no seu computador que roda a skill `po-spec-review` pelo **Claude Code** (o login da sua assinatura, sem chave de API). Você envia a especificação, recebe a revisão e o PDF das histórias com tasks, e pode subir tudo para o Azure DevOps.

## Como rodar

```powershell
python -m streamlit run spec_review_page.py
```

Abra o endereço que o Streamlit mostrar (normalmente http://localhost:8501).

## Antes de usar

- O Claude Code precisa estar instalado e **logado**. Se a página disser que o login expirou, abra um terminal, rode `claude` e entre de novo.
- A skill precisa estar instalada: `python -m scripts.install_skill`.
- O executável é procurado no PATH e em `C:\Users\<você>\.local\bin\claude.exe`.

## O que a página faz

1. Você envia um PDF (ou TXT/MD) ou cola o texto e clica em **Revisar**. A saída aparece em tempo real.
2. Ao terminar, você baixa o **PDF das histórias** (título, descrição, critérios de aceite e tasks).
3. Para o Azure: informe organização, projeto e token, clique em **Ver prévia** (não envia nada) e, só depois, em **Confirmar e enviar ao Azure**. Mudar a organização ou o projeto depois da prévia desabilita o envio de novo.

## Limites e cuidados

- Uso **local**. A revisão consome o limite de uso da sua assinatura. Os termos do plano para esse uso automatizado não foram verificados: confira antes.
- O documento é enviado ao Claude, como quando você o anexa no chat. Ele fica numa pasta temporária que é apagada ao final.
- O token do Azure fica só na sessão do navegador e nunca é gravado.
- Os testes usam um Claude Code falso. **Uma revisão de verdade ainda não foi executada**, então a qualidade da saída e o comportamento do modo automático da skill precisam ser conferidos por você.
- Faça o primeiro envio ao Azure num projeto de sandbox.
