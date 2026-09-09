# Baixatudo

App desktop em Python para baixar videos de links publicos do YouTube, Pornhub e XVideos usando `yt-dlp`.

## Como abrir

1. De dois cliques em `Iniciar Baixatudo.cmd`.
2. Clique em `Instalar/atualizar ferramentas` na primeira execucao.
3. Cole um ou mais links, escolha a pasta, confirme o uso permitido e clique em `Baixar`.

## Observacoes

- Use apenas videos que voce possui, tem permissao para baixar ou que os termos do site permitam.
- O instalador `dist/Baixatudo-Setup.exe` inclui o app e o `yt-dlp`, mas o computador ainda precisa ter Python 3 instalado.
- O app nao inclui login, cookies, paywall, DRM ou recursos para contornar restricoes.
- A opcao `MP4 compativel` costuma funcionar sem FFmpeg.
- `MP4 ate 1080p`, `Melhor qualidade` e `Somente audio MP3` instalam automaticamente FFmpeg e ffprobe quando ausentes, antes de iniciar o download. A primeira instalacao precisa de internet e baixa aproximadamente 100 MB.
- As ferramentas ficam em `tools/`, sem alterar o PATH do Windows. O app informa essa pasta ao yt-dlp e verifica a presenca dos dois executaveis, inclusive em pacotes portateis.
- O FFmpeg para Windows 64 bits vem de [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), fornecedor indicado pelo [projeto FFmpeg](https://ffmpeg.org/download.html). O pacote e validado com SHA-256 antes da instalacao.
- Se um download anterior terminou em `.webm` com erro de FFmpeg, repita o mesmo link, pasta e opcao MP3. O yt-dlp pode reaproveitar o arquivo existente e concluir a conversao.

## Arquivos

Os detalhes da correcao e da validacao estao em [RESULTADOS.md](RESULTADOS.md). Para executar os testes: `python -m unittest discover -s tests -v`.

- `baixatudo.pyw`: interface grafica em Python/Tkinter.
- `Iniciar Baixatudo.cmd`: atalho para abrir com duplo clique.
- `tools/yt-dlp.exe`: criado automaticamente quando voce usa o botao de instalacao.
- `dist/Baixatudo-Setup.exe`: instalador de 1 arquivo, gerado pelo script `installer/build_installer.ps1`.
