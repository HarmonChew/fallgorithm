# Experiment 007 — stranded edge columns (development only)

Status: development finding, no held-out evaluation.

## Autopsy of Experiment 006's 13 deaths

`../006-level29-survival/probes/autopsy.py RECORD SEED N survival_plan` replays a
`survival_plan` game. In 12 of the 13 deaths an edge column (column 0 in 11
games, column 9 in one) sat four or more rows below the stack for much of the
last 40 pieces, and only 5–8 lines cleared in those 40 pieces. At one row per
frame a piece reaches an edge column only while the columns between it and the
spawn point are low. Once they grow, nothing can land on the edge column, every
row keeps a gap, and the stack climbs. The deaths come quickly, 26 to 153 pieces
after the board was last healthy (at most five rows, at most one hole).

## Development comparison

`probes/variants.py` uses Experiment 006's 30 seeds, whose outcomes were already
known, with a 200,000-frame cap. From level 28 it charges `weight` per column on
which no reachable placement of any of the seven pieces lands a cell (scored on
the board the preview leaves), and extends `beam` paths into the unknown ply.
`probes/development.json` holds the result.

| variant | top-outs / 30 | mean lines | min lines | mean score |
| --- | --- | --- | --- | --- |
| `survival_plan` (beam 2) | 7 | 1,884 | 589 | 9.12M |
| beam 4 | 4 | 1,997 | 643 | 9.92M |
| beam 8 | 4 | 2,044 | 1,112 | 10.21M |
| weight 5 | 5 | 1,939 | 586 | 9.60M |
| weight 20 | 5 | 1,947 | 599 | 9.66M |
| weight 5, beam 8 | 3 | 2,041 | 1,091 | 10.23M |
| weight 20, beam 8 | 4 | 2,018 | 1,096 | 10.05M |

A first version of the penalty counted columns any piece *covers*. It changed no
decision, because a flat piece laid across a stranded column still covers it
while roofing it into a hole.

Both changes help a little, but the differences are a few games out of 30 and
within what seed noise could produce. The trap builds over more pieces than the
three-piece search sees.
