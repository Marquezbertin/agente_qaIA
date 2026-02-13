# Guia de Prompts - QA Agent

Este documento contém prompts de referência para todas as funcionalidades do QA Agent.
Use estes exemplos como base para interagir com o agente.

---

## 1. EXECUÇÃO DE TESTES (Pytest)

### Executar Testes por Pasta
```
Execute os testes da pasta security_tests
```
```
Rode todos os testes de API na pasta api_tests
```

### Executar por Marker
```
Execute os testes de smoke do ambiente UAT
```
```
Rode apenas os testes marcados como 'critical'
```

### Executar Teste Específico
```
Execute o teste test_login.py da pasta e2e_tests
```
```
Rode o arquivo security_tests/auth/test_token_validation.py
```

### Executar com Verbosidade
```
Execute os testes de regressão com saída detalhada
```
```
Rode os testes de segurança e mostre todos os prints
```

---

## 2. LEITURA E ESCRITA DE ARQUIVOS

### Ler Arquivos
```
Mostre o conteúdo do arquivo conftest.py
```
```
Leia o arquivo pytest.ini e explique as configurações
```

### Analisar Código
```
Analise o código do arquivo test_api_login.py e sugira melhorias
```
```
Leia o arquivo de configuração .env e verifique se está correto
```

### Criar/Editar Arquivos
```
Crie um novo teste de API para validar o endpoint de CPF
```
```
Adicione um novo caso de teste no arquivo test_security.py para SQL injection
```

### Listar Arquivos
```
Liste todos os arquivos de teste na pasta security_tests
```
```
Mostre a estrutura de pastas do projeto de testes
```

---

## 3. BUSCA EM CÓDIGO

### Buscar por Padrão
```
Busque por 'SQL injection' em todos os arquivos de teste
```
```
Encontre todos os lugares onde usamos 'assert response.status_code'
```

### Buscar Função/Classe
```
Encontre onde está definida a função validate_cpf
```
```
Busque todas as classes que herdam de BaseTest
```

### Buscar por Vulnerabilidade
```
Busque por possíveis vulnerabilidades XSS nos testes
```
```
Encontre todos os testes que validam autenticação
```

---

## 4. MONITORAMENTO DE USUÁRIO (Browser Visível)

### Iniciar Monitoramento
```
Abra a página http://localhost:3000/login e monitore minhas ações
```
```
Inicie o monitoramento da página de cadastro para eu testar manualmente
```

### Durante o Monitoramento
```
Capture o estado atual da página
```
```
Registre um screenshot agora
```

### Encerrar Monitoramento
```
Terminei de navegar, encerre o monitoramento e me mostre os dados
```
```
Pare o monitoramento e gere um relatório das ações capturadas
```

### Gerar Teste a partir do Monitoramento
```
Com base nas ações que você capturou, crie um script de teste E2E
```
```
Use os dados do monitoramento para criar um caso de teste automatizado
```

---

## 5. AUTOMAÇÃO DE BROWSER (Headless)

### Navegar e Capturar
```
Acesse https://jsonplaceholder.typicode.com e tire um screenshot
```
```
Navegue para a página de login e capture o estado atual
```

### Verificar Erros
```
Verifique se há erros visíveis na página https://reqres.in
```
```
Acesse a página de produtos e verifique se carrega corretamente
```

### Executar Testes E2E
```
Execute o teste Cypress de login
```
```
Rode o teste Playwright do fluxo de cadastro
```

---

## 6. GESTÃO DE BUGS

### Criar Bug
```
Registre um bug: O botão de login não responde quando clicado duas vezes rapidamente
```
```
Crie um bug crítico: API retorna 500 ao enviar CPF com pontuação
```

### Criar Bug Detalhado
```
Registre um bug com os seguintes detalhes:
- Título: Campo de email aceita formato inválido
- Severidade: média
- Passos: 1. Acessar login 2. Digitar "teste@" 3. Clicar em entrar
- Esperado: Mensagem de erro
- Atual: Sistema aceita e trava
```
```
Crie um bug de segurança:
- Título: Token JWT não expira após logout
- Ambiente: UAT
- Severidade: alta
- Descrição: Após fazer logout, o token anterior ainda funciona por 24h
```

### Listar e Consultar Bugs
```
Liste todos os bugs abertos
```
```
Mostre os bugs críticos que ainda não foram resolvidos
```
```
Quais bugs temos no ambiente de UAT?
```
```
Busque bugs relacionados a autenticação
```

### Atualizar Bug
```
Atualize o bug #1 para status 'em progresso' e atribua para João
```
```
Marque o bug #5 como resolvido e adicione a nota: Corrigido na versão 2.1
```

### Obter Detalhes
```
Mostre os detalhes completos do bug #3
```
```
Quais são os passos para reproduzir o bug #7?
```

---

## 7. GESTÃO DE FEATURES

### Criar Feature
```
Crie uma feature: Implementar autenticação com Google OAuth
```
```
Registre uma nova feature:
- Título: Exportar relatórios em PDF
- Descrição: Permitir que usuários exportem seus relatórios em formato PDF
- Critérios de aceite: 1. Botão de exportar visível 2. PDF gerado em até 5s 3. Incluir logo da empresa
- Prioridade: 2
```

### Listar Features
```
Liste todas as features no backlog
```
```
Quais features estão em desenvolvimento?
```
```
Mostre as features planejadas para a próxima sprint
```

### Atualizar Feature
```
Mova a feature #2 para status 'em teste'
```
```
Atualize a prioridade da feature #5 para alta (prioridade 1)
```

---

## 8. CASOS DE TESTE

### Criar Caso de Teste Simples
```
Crie um caso de teste para validar login com email e senha válidos
```
```
Crie um teste para verificar se o CPF é validado corretamente
```

### Criar Caso de Teste Detalhado
```
Crie um caso de teste completo:
- Título: Validar login com credenciais válidas
- Pré-condições: Usuário cadastrado no sistema
- Passos:
  1. Acessar página de login
  2. Preencher email válido
  3. Preencher senha correta
  4. Clicar em Entrar
- Resultado esperado: Usuário redirecionado para dashboard
- Categoria: smoke
- Prioridade: alta
```
```
Crie um caso de teste de segurança:
- Título: Verificar proteção contra SQL Injection no login
- Passos:
  1. Acessar página de login
  2. No campo email, inserir: ' OR '1'='1
  3. No campo senha, inserir: ' OR '1'='1
  4. Clicar em Entrar
- Resultado esperado: Sistema rejeita a tentativa e mostra erro genérico
- Categoria: security
- Tags: sql-injection, owasp
```

### Criar Caso de Teste Vinculado
```
Crie um caso de teste para a feature #3 (autenticação OAuth)
```
```
Crie um teste de regressão para o bug #7 que foi corrigido
```

### Listar Casos de Teste
```
Liste todos os casos de teste de segurança
```
```
Mostre os casos de teste da categoria 'smoke'
```
```
Quais testes temos para a feature #2?
```

### Obter Detalhes
```
Mostre os passos completos do caso de teste #5
```
```
Quais são as pré-condições do teste #12?
```

---

## 9. PLANOS DE TESTE

### Criar Plano de Teste
```
Crie um plano de teste para a Sprint 15
```
```
Crie um plano de teste:
- Nome: Plano de Regressão v2.0
- Objetivo: Validar todas as funcionalidades antes do release
- Escopo: Login, Cadastro, Consultas, Relatórios
- Ambiente: UAT
- Data início: 2026-02-10
- Data fim: 2026-02-15
```

### Adicionar Casos ao Plano
```
Adicione o caso de teste #1 ao plano #1
```
```
Inclua os casos de teste #3, #5 e #7 no plano de regressão
```
```
Adicione todos os casos de teste de smoke ao plano #2
```

### Listar Planos
```
Liste todos os planos de teste
```
```
Quais planos estão em execução?
```
```
Mostre os planos de teste concluídos
```

### Obter Detalhes do Plano
```
Mostre os detalhes do plano de teste #1 incluindo todos os casos
```
```
Quais casos de teste fazem parte do plano de regressão?
```

### Atualizar Status
```
Inicie a execução do plano #1 (mude para 'em progresso')
```
```
Marque o plano #3 como concluído
```

---

## 10. EXECUÇÃO DE TESTES (Registro Manual)

### Registrar Execução Passou
```
Registre que o caso de teste #1 passou
```
```
O teste #5 passou no ambiente UAT, registre com tempo de 45 segundos
```

### Registrar Execução Falhou
```
Registre que o teste #3 falhou com a nota: Botão não clicável
```
```
O caso #7 falhou no ambiente de produção, registre com evidência screenshot_erro.png
```

### Registrar Execução Bloqueada
```
Registre o teste #2 como bloqueado - ambiente indisponível
```
```
O teste #9 está bloqueado aguardando deploy, registre isso
```

### Registrar Execução em Plano
```
Registre que o teste #1 do plano #1 passou
```
```
Execute e registre os resultados do caso #5 dentro do plano de regressão
```

### Consultar Histórico
```
Mostre o histórico de execuções do caso de teste #3
```
```
Quais foram os resultados das execuções do plano #1?
```
```
Liste as últimas 10 execuções de teste
```

---

## 11. RELATÓRIOS

### Relatório Geral
```
Gere um relatório de QA com o status atual
```
```
Me dê um resumo geral dos testes: bugs, casos e execuções
```

### Relatório de Plano
```
Gere o relatório do plano de teste #1
```
```
Qual é a taxa de sucesso do plano de regressão?
```

### Análise de Métricas
```
Quantos bugs críticos temos abertos?
```
```
Qual é a porcentagem de testes passando?
```
```
Me dê as estatísticas de execução da última semana
```

---

## 12. MEMÓRIA E APRENDIZADO

### Ensinar ao Agente
```
Lembre que o endpoint de CPF precisa do header X-API-Key
```
```
Aprenda: Para testes de biometria, sempre usar o ambiente UAT
```

### Salvar Conhecimento
```
Salve este aprendizado de segurança: Sempre testar SQL injection em campos de busca
```
```
Guarde esta boa prática: Usar data-testid para seletores em testes E2E
```

### Consultar Memória
```
O que você sabe sobre testes de API?
```
```
O que você aprendeu sobre o ambiente UAT?
```
```
Busque nos seus aprendizados sobre autenticação
```

### Histórico de Testes
```
Mostre o histórico das últimas execuções de teste
```
```
Quais testes falharam recentemente?
```

---

## 13. COMANDOS DE TERMINAL

### Git
```
Mostre o status do git do projeto
```
```
Faça commit das alterações com a mensagem 'Adiciona testes de login'
```

### Instalação
```
Instale as dependências do requirements.txt
```
```
Atualize o Selenium para a última versão
```

### Verificação
```
Verifique se o Python está instalado corretamente
```
```
Liste as bibliotecas instaladas no ambiente
```

---

## 14. DOCUMENTAÇÃO WEB

### Consultar Documentação
```
Acesse a documentação da API em https://reqres.in e me explique os endpoints disponíveis
```
```
Leia a documentação do Pytest sobre fixtures e me resuma
```

### Verificar Disponibilidade
```
Verifique se a API esta online
```
```
Acesse https://jsonplaceholder.typicode.com e confirme se o site está funcionando
```

---

## 15. ANÁLISE E SUGESTÕES

### Analisar Código
```
Analise o arquivo test_login.py e sugira melhorias
```
```
Revise os testes de segurança e identifique gaps de cobertura
```

### Sugerir Testes
```
Sugira casos de teste para a funcionalidade de reset de senha
```
```
Que testes de segurança devo criar para o endpoint de autenticação?
```

### Identificar Problemas
```
Analise os testes que estão falhando e sugira correções
```
```
Identifique testes duplicados no projeto
```

---

## 16. FLUXOS COMPLETOS

### Fluxo de Bug
```
Encontrei um problema no login. Me ajude a:
1. Registrar o bug
2. Criar um caso de teste para ele
3. Adicionar ao plano de regressão
```

### Fluxo de Feature
```
Vamos criar os testes para a nova feature de pagamento:
1. Registre a feature
2. Crie 5 casos de teste para ela
3. Crie um plano de teste
4. Adicione os casos ao plano
```

### Fluxo de Release
```
Prepare o ambiente para o release:
1. Execute os testes de smoke
2. Execute os testes de regressão
3. Gere um relatório completo
4. Liste os bugs abertos que bloqueiam
```

### Fluxo de Teste Exploratório
```
Vou fazer um teste exploratório:
1. Abra a página de login e monitore minhas ações
2. [Após navegar] Capture tudo que fiz
3. [Ao terminar] Encerre e crie um caso de teste baseado nas ações
```

---

## DICAS DE USO

### Ser Específico
Em vez de: "Crie um teste"
Use: "Crie um caso de teste de login com email válido e senha incorreta, categoria security"

### Fornecer Contexto
Em vez de: "Liste bugs"
Use: "Liste os bugs críticos abertos no ambiente UAT"

### Pedir Confirmação
"Antes de executar os testes, me mostre quais arquivos serão rodados"

### Combinar Ações
"Execute os testes de smoke e depois gere um relatório com os resultados"

### Usar Referências
"Crie um caso de teste similar ao #5, mas para o fluxo de cadastro"

---

## ATALHOS ÚTEIS

| Ação | Prompt Rápido |
|------|---------------|
| Status geral | "Me dê um resumo de QA" |
| Bugs abertos | "Bugs abertos" |
| Testes falhando | "Quais testes falharam?" |
| Executar smoke | "Rode smoke" |
| Relatório | "Gere relatório" |
| Monitorar | "Monitore [URL]" |

## você poderia pedir ao agente coisas como:
  - "Rode os testes de validação de CPF usando CPFs reais do banco"
  - "Pegue 5 CNPJs do banco e teste a API de consulta"
  - "Use um CPF do banco para testar o login"

---

*Documento gerado para o QA Agent - Assistente de Quality Assurance*
*Última atualização: 2026-02-05*
