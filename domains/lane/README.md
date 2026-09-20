# domains/lane

Lane Cost & Exception. Quotes all-in USD / USD/mi from the cost model (not a prompt). Drafts one local SMS if the assigned truck is late to pickup+15 (checked before delivery). Delivered requires driver and receiver confirm. No DAT / Truckstop / live broker.

```
python -m domains.lane quote --load L-07
python -m domains.lane watch --load L-07 --truck T-07
python -m domains.lane book --load L-07 --truck T-07 --cap-usd-per-mi 2.5
python -m domains.lane confirm --load L-07 --party driver
python -m evals.lane_harness
```

Default autonomy is `recommend`. `book` is `act_under_cap` and writes a local artifact only for fixture trucks under the cap.
