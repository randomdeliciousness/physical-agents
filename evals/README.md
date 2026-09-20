# Evals

Each domain harness prints one line and exits 0 on pass:

```
DOMAIN=<name> PASS=<0|1> METRIC=<name> VALUE=<number> BASELINE=<number> UNIT=<unit>
```

Harness files are created in stages 01–05 by Grok Build. Do not put live network calls here.
