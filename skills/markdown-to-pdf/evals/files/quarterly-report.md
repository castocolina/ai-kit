# Quarterly revenue report

Revenue grew in every region this quarter, led by the North America team. The chart
below shows the three regional totals, and the flow below shows how a booked order
becomes recognized revenue.

![Revenue by region](img/revenue.svg)

```mermaid
flowchart TD
  A[Order booked] --> B[Delivered]
  B --> C[Revenue recognized]
```
