# Programa de indicação de clientes

## Problema

Conquistar clientes por canais pagos está cada vez mais caro, e clientes satisfeitos não têm um jeito simples de recomendar a loja. O marketing hoje não consegue medir o boca a boca, então ele não é incentivado nem financiado.

## Situação atual (AS IS)

- Clientes não conseguem convidar amigos nem ganhar recompensa por novos clientes.
- A aquisição depende só de canais pagos.

## Situação futura (TO BE)

- Cada cliente tem um link de indicação único.
- O amigo que chega pelo link vê o desconto antes do checkout.
- Quem indicou recebe o crédito depois do primeiro pedido concluído do amigo.

## Personas

- Cliente recorrente: quer recomendar a loja e ser recompensado sem precisar falar com o suporte
- Amigo indicado: quer saber que a oferta é real antes de criar uma conta
- Dono do programa (marketing): quer crescer a aquisição e controlar o custo das recompensas

## Objetivos

- Aumentar a participação de novos clientes adquiridos por recomendação
- Recompensar quem indica e quem é indicado de um jeito simples de entender
- Manter o custo do programa previsível e resistente a fraudes

## Métricas de sucesso

- Participação de novos clientes adquiridos por indicação: aumentar (linha de base não informada)
- Taxa de conversão de indicados (amigos convidados que fazem o primeiro pedido): aumentar (linha de base não informada)
- Custo de recompensa por cliente indicado: ficar abaixo do custo de aquisição em canais pagos

## Sistemas e módulos

- Loja online - Checkout
- Conta do cliente - Área de indicação

## Dentro do escopo

- Link de indicação único por cliente
- Desconto para o amigo e crédito para quem indica após o primeiro pedido do amigo
- Visão de status dos convites para quem indica
- Prevenção básica de fraude

## Fora do escopo

- Indicação por APIs de redes sociais ou importação de contatos
- Recompensas multinível ou em faixas

## Requisitos

- O sistema deve dar a cada cliente um link de indicação único
- O sistema deve mostrar o desconto do amigo antes do checkout quando ele chega por um link de indicação
- O sistema deve creditar quem indicou depois que o primeiro pedido do amigo for concluído
- O sistema deve permitir que quem indica veja o status de cada convite
- O sistema deve bloquear autoindicação e recompensas repetidas para o mesmo amigo

## Regras de negócio

- RN01: Um link de indicação pertence a exatamente um cliente.
- RN02: Quem indicou só recebe o crédito depois que o primeiro pedido do amigo é concluído.
- RN03: Um cliente não pode indicar a si mesmo, e um amigo só pode gerar uma recompensa.

## Retornos esperados

- Experiência: participação de novos clientes adquiridos por indicação
- Financeiro: custo de aquisição por cliente (linha de base não informada)

## Riscos

- Fraude de recompensa com contas falsas - mitigação: recompensar apenas após um primeiro pedido concluído e pago
- Custo do desconto acima do orçamento - mitigação: limitar o total de recompensas por cliente por mês

## Premissas

- Premissa: a recompensa é crédito na loja, não dinheiro; a ideia não diz qual
- Premissa: os clientes já têm conta e conseguem entrar

## Perguntas em aberto

- Quais são os valores das recompensas e quem as financia?
- Qual é o custo de aquisição por cliente hoje, para definir o ponto de equilíbrio?

## Histórias de usuário

### S1 — Copiar meu link de indicação

Como cliente recorrente, quero copiar meu link de indicação na página da minha conta em um passo para possa compartilhá-lo sem precisar falar com o suporte

Compartilhar e acompanhar · Must · 3 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: Link de indicação é copiado para compartilhamento
  Dado um cliente recorrente está autenticado
  Quando o cliente escolhe copiar seu link de indicação
  Então o link fica disponível para colar
  E o link identifica o cliente como indicador

Cenário: Cada cliente tem um link diferente
  Dado dois clientes recorrentes estão autenticados
  Quando cada um abre seu link de indicação
  Então os dois links são diferentes
```

### S2 — Receber crédito pelo primeiro pedido do amigo

Como cliente recorrente, quero receber crédito na loja quando meu amigo concluir um primeiro pedido para seja recompensado por recomendar a loja

Compartilhar e acompanhar · Must · 5 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: Quem indica é creditado após o primeiro pedido pago
  Dado um amigo chegou pelo link de indicação de um cliente
  E o amigo fez e pagou um primeiro pedido
  Quando o pedido é marcado como concluído
  Então quem indicou recebe o crédito de indicação
  E quem indicou é avisado do crédito

Cenário: Não há crédito para pedido não pago
  Dado um amigo chegou por um link de indicação
  E o pagamento do pedido do amigo falhou
  Quando o pedido é cancelado
  Então quem indicou não recebe crédito

Cenário: O crédito é dado uma única vez por amigo
  Dado quem indicou já foi creditado por um amigo
  Quando o amigo conclui um segundo pedido
  Então quem indicou não recebe crédito adicional
```

### S3 — Ver o desconto do amigo pelo link de indicação

Como amigo indicado, quero ver meu desconto ao chegar por um link de indicação e de novo no checkout para saiba que a oferta é real antes de comprar

Experiência do amigo indicado · Must · 3 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: O desconto aparece na chegada
  Dado um visitante abre um link de indicação válido
  Quando a página da loja carrega
  Então o visitante vê a oferta de desconto para amigos
  E o visitante vê quem o convidou

Cenário: O desconto é aplicado no checkout
  Dado um visitante chegou por um link de indicação válido e adicionou itens ao carrinho
  Quando o visitante chega ao checkout
  Então o desconto aparece como uma linha no resumo do pedido

Cenário: Link inválido não mostra desconto
  Dado um visitante abre um link de indicação que não existe
  Quando a página da loja carrega
  Então nenhum desconto é exibido
  E o visitante ainda pode navegar e comprar pelos preços normais
```

### S4 — Acompanhar o status dos meus convites

Como cliente recorrente, quero ver se cada amigo convidado já se cadastrou ou fez pedido para saiba quando esperar meu crédito

Experiência do amigo indicado · Should · 5 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: Quem indica vê cada etapa
  Dado um cliente convidou três amigos, um se cadastrou e um fez pedido
  Quando o cliente abre a página de indicações
  Então o cliente vê as contagens de convidados, cadastrados e com pedido

Cenário: O estado vazio explica como começar
  Dado um cliente ainda não compartilhou o link
  Quando o cliente abre a página de indicações
  Então o cliente vê como o programa funciona e o link para copiar
```

### S5 — Bloquear autoindicação

Como dono do programa, quero que o sistema recuse recompensas quando quem indica e o amigo forem a mesma pessoa para o custo das recompensas não seja desperdiçado com indicações falsas

Integridade do programa · Should · 5 pts

**Critérios de aceite**

```gherkin
# language: pt
Cenário: O mesmo cliente não pode se recompensar
  Dado um cliente abre o próprio link de indicação em uma conta nova com o mesmo meio de pagamento
  Quando a conta nova conclui um primeiro pedido
  Então nenhum desconto é dado à conta nova
  E nenhum crédito é dado a quem indicou

Cenário: Indicação legítima não é afetada
  Dado um amigo com outra conta e outro meio de pagamento chega por um link de indicação
  Quando o amigo conclui um primeiro pedido
  Então o desconto e o crédito são concedidos
```
