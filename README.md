# Biome tagging utility for the MGnify backlog schema
## Installation
```bash
pip install -U git+git://github.com/EBI-Metagenomics/emg-backlog-schema.git;
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

## Usage:
Run the following to start the tagging UI.
```bash
    tag-biome
```