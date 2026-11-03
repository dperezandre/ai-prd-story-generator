# Recuperação de carrinho abandonado

## Problema

Muitos compradores colocam itens no carrinho e saem sem pagar. A loja não faz nenhum acompanhamento, então clientes interessados são perdidos, e um acompanhamento agressivo demais pode incomodá-los e violar regras de consentimento.

## Personas

- Comprador indeciso: deixou itens no carrinho e pode voltar se for lembrado no momento certo
- Gerente de e-commerce: quer recuperar receita sem prejudicar a marca

## Objetivos

- Recuperar uma parcela mensurável dos carrinhos abandonados
- Manter os lembretes relevantes, em número limitado e fáceis de cancelar

## Métricas de sucesso

- Taxa de carrinhos recuperados (carrinhos abandonados que terminam em pedido pago): aumentar (linha de base não informada)
- Taxa de descadastro dos e-mails de lembrete: manter baixa (limite não informado)

## Dentro do escopo

- E-mail de lembrete depois que o carrinho é abandonado
- Um lembrete de acompanhamento
- Link que restaura o carrinho
- Regras de descadastro e de parada após a compra

## Fora do escopo

- Lembretes por SMS ou push
- Ofertas de desconto personalizadas

## Requisitos

- O sistema deve enviar um e-mail de lembrete ao comprador autenticado que abandonou um carrinho
- O sistema deve enviar no máximo um lembrete de acompanhamento
- O sistema deve restaurar o conteúdo do carrinho quando o comprador seguir o link do e-mail
- O sistema deve interromper os lembretes quando o comprador concluir uma compra
- O sistema deve respeitar o pedido de descadastro em todo lembrete

## Riscos

- Regras de privacidade e consentimento para e-mail de marketing - mitigação: enviar apenas a compradores que aceitaram comunicações, com descadastro em um clique
- Itens esgotados quando o comprador volta - mitigação: informar quais itens deixaram de estar disponíveis

## Premissas

- Premissa: um carrinho é considerado abandonado após 1 hora sem checkout; a ideia não define isso
- Premissa: só compradores autenticados podem ser alcançados, pois a loja tem o e-mail deles

## Perguntas em aberto

- Qual é o tempo de espera certo antes do primeiro lembrete?
- Que registro de consentimento a loja mantém para e-mail de marketing?

## Histórias de usuário

### S1 — Enviar lembrete após o abandono do carrinho

Como comprador indeciso, quero receber um e-mail me lembrando dos itens que deixei no carrinho para possa concluir a compra sem procurar tudo de novo

E-mails de lembrete · Must · 5 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: O lembrete é enviado após o tempo de espera
  Dado um comprador autenticado que aceitou e-mails deixou itens no carrinho
  Quando uma hora passa sem checkout
  Então o comprador recebe um lembrete com os itens deixados no carrinho

Cenário: Sem consentimento, sem lembrete
  Dado um comprador autenticado que não aceitou e-mails de marketing deixou itens no carrinho
  Quando uma hora passa sem checkout
  Então nenhum lembrete é enviado
```

### S2 — Enviar um acompanhamento após 24 horas

Como gerente de e-commerce, quero um único lembrete de acompanhamento 24 horas após o primeiro, quando o carrinho continua aberto para mais compradores voltem sem serem contatados em excesso

E-mails de lembrete · Should · 3 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: O acompanhamento é enviado uma vez
  Dado um comprador recebeu o primeiro lembrete e não comprou
  Quando 24 horas se passam
  Então o comprador recebe um lembrete de acompanhamento

Cenário: Não há terceiro lembrete
  Dado um comprador recebeu o lembrete e o acompanhamento e não comprou
  Quando mais tempo passa
  Então nenhum outro lembrete é enviado
```

### S3 — Restaurar meu carrinho pelo link do e-mail

Como comprador indeciso, quero voltar a um carrinho já com meus itens ao seguir o link do e-mail para possa ir direto ao checkout

E-mails de lembrete · Must · 5 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: O carrinho é restaurado
  Dado um comprador recebeu um lembrete de um carrinho com dois itens
  Quando o comprador segue o link
  Então o carrinho mostra os mesmos dois itens
  E o comprador pode seguir para o checkout

Cenário: Itens indisponíveis são explicados
  Dado um dos dois itens está esgotado
  Quando o comprador segue o link
  Então o carrinho contém o item disponível
  E o comprador é informado de qual item deixou de estar disponível
```

### S4 — Descadastrar-me dos lembretes

Como comprador indeciso, quero parar de receber lembretes de carrinho com um clique em qualquer lembrete para minha escolha seja respeitada imediatamente

Controle do cliente · Must · 2 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: O descadastro vale imediatamente
  Dado um comprador recebeu um lembrete
  Quando o comprador usa o link de descadastro
  Então o comprador recebe a confirmação de descadastro
  E nenhum outro lembrete de carrinho é enviado

Cenário: O acompanhamento pendente é cancelado
  Dado um comprador recebeu o primeiro lembrete e tem um acompanhamento agendado
  Quando o comprador se descadastra
  Então o acompanhamento agendado não é enviado
```

### S5 — Parar os lembretes após a compra

Como comprador indeciso, quero que os lembretes parem assim que eu concluir meu pedido para não seja incomodado por algo que já comprei

Controle do cliente · Should · 3 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: O lembrete para após a compra
  Dado um comprador recebeu o primeiro lembrete
  Quando o comprador conclui o pedido antes do acompanhamento
  Então o acompanhamento não é enviado

Cenário: Compra parcial mantém o restante
  Dado um comprador deixou três itens e comprou um deles
  Quando chega a hora do acompanhamento
  Então o acompanhamento lista apenas os dois itens restantes
```
