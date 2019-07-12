# Biome tagging utility for the MGnify backlog schema

## Python version support
3.6

## Installation
```bash
pip install -U git+git://github.com/EBI-Metagenomics/emg-backlog-schema.git;
pip install -U git+git://github.com/EBI-Metagenomics/ena-api-handler.git
pip install -U git+git://github.com/EBI-Metagenomics/ebi-metagenomics-libs.git;
pip install -U git+git://github.com/EBI-Metagenomics/biome_prediction.git;
pip install -U git+git://github.com/EBI-Metagenomics/biome_tagger.git;
```

A config file needs to be placed at `~/backlog/config.yaml` OR pointed to by environment variable `BACKLOG_CONFIG`
The format of this file is:

```yaml
backlog:
  databases:
    default:
      ENGINE: 'django.db.backends.mysql'
      NAME: 'schema_name'
      USER: 'user'
      PASSWORD: 'pw'
      HOST: 'localhost'
      PORT: port
      DB: 'emg_backlog_2'
    prod:
      ENGINE: 'django.db.backends.mysql'
      NAME: 'emg_backlog_2'
      USER: 'admin'
      PASSWORD: 'pw'
      HOST: 'host'
      PORT: port
      DB: 'emg_backlog_2'
```
## Tagging private studies
To tag private studies, the ena API credentials need to be loaded using the env variables ENA_API_USER and ENA_API_PASSWORD.
## Usage:
Run the following to start the tagging UI.
```bash
    tag-biome
```
