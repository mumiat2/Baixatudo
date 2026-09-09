# Resultados da correcao — 09/09/2026

## Problema

O download de audio terminava em WebM, mas a conversao para MP3 falhava com `Postprocessing: ffprobe and ffmpeg not found`.

## Correcao

- Detecta FFmpeg e ffprobe juntos nas pastas locais, no pacote do aplicativo ou no PATH.
- Passa a pasta encontrada ao yt-dlp com `--ffmpeg-location`.
- Instala as ferramentas ausentes antes de baixar nos modos que precisam de conversao ou mesclagem.
- Verifica SHA-256 do pacote e executa `-version` dos dois programas antes de instala-los.
- Interrompe o processo antes do download se a instalacao das dependencias falhar.
- Atualiza o botao de instalacao e impede novos cliques enquanto uma tarefa esta iniciando.

## Validacao realizada

Ambiente: Windows, yt-dlp 2026.08.19.

Comando dos testes: `python -m unittest discover -s tests -v`.

Resultado: **3 testes aprovados**.

1. Exige os dois executaveis e reconhece a pasta `ffmpeg/bin`.
2. Envia corretamente uma pasta com espacos em `--ffmpeg-location`.
3. Nao inicia o download quando a instalacao das dependencias falha.

Teste de integracao pelo fluxo de download do aplicativo:

- Link: https://youtu.be/I57KBXZD77Q
- Opcao: `Somente audio MP3`.
- Download do formato 251 e conversao concluidos com sucesso.
- Codec confirmado pelo ffprobe: `mp3`.
- Duracao confirmada: 85,170813 segundos.

O instalador `dist/Baixatudo-Setup.exe` foi recompilado com a correcao. Ele inclui o aplicativo e yt-dlp; FFmpeg e ffprobe sao instalados pelo aplicativo quando necessarios. Python 3 precisa estar instalado no computador de destino.

Os arquivos de audio usados na verificacao permanecem apenas no ambiente local. O resultado publicado consiste neste relatorio, no codigo, nos testes e no instalador.

## Limites da validacao

O teste de integracao cobre o link acima em modo MP3. Nao representa uma verificacao de todos os sites, playlists ou qualidades disponiveis.
