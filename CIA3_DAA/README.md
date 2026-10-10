# Smart Society Shuttle — Interactive Dynamic Programming and Routing

## Problem Statement
A shuttle runs inside a residential society and connects its blocks and facilities (Main Gate, Blocks A–C, Junctions 1–2, Market, Hospital, School, Temple) to the Metro Station. Roads take longer in peak hours and are sometimes blocked.

The system must answer two questions:
1. What is the cheapest road route between two locations?
2. In which order should the shuttle visit several mandatory stops so the total travel cost is as low as possible?

**Input:** road network (11 locations, 17 roads), start, destination, required stops, traffic condition (Normal ×1.0, Morning Peak ×1.35, Evening Peak ×1.5), blocked roads.
**Output:** shortest route and cost, optimal visiting order, road-by-road route, total cost.

All roads, traffic factors and costs are simulated (estimated travel minutes). Nothing uses real GPS or live traffic.

## Algorithms Used
* **Dijkstra's algorithm** finds the shortest road between two locations. It is also run from every selected location to build the cost matrix for the stop-ordering step. Time O(V²), space O(V).
* **Travelling Salesman Problem with Dynamic Programming** finds the exact best visiting order using the backward recurrence:
  * `g(i, ∅) = c[i][t]`
  * `g(i, S) = min over j ∈ S of ( c[i][j] + g(j, S − {j}) )`
  * `Answer = g(1, V − {1})`

  Time O(n²·2ⁿ), space O(n·2ⁿ). It has two modes:
  * *Textbook tour:* start at Main Gate, visit all selected stops, return to Main Gate.
  * *Shuttle-to-Metro:* visit all required stops once and finish at the Metro Station.

## Solution
1. Apply the traffic multiplier and remove blocked roads (in both directions) from a copy of the road network.
2. Run Dijkstra between every pair of selected locations to build a complete cost matrix. This gives a finite cost even when two stops have no direct road, and it stores the road path for each pair.
3. Run the dynamic programming recurrence on the matrix. Every g(i, S) value and its best next stop is stored.
4. Follow the stored choices to rebuild the optimal order.
5. Replace each leg with its stored road path to get the real road-by-road route. Its cost equals the DP answer.
6. If a selected location cannot be reached, an error is shown and no route is displayed.

The app shows each calculation step by step, with a Predict mode, an animated shuttle on the final route, a society graph and map view, 22 automated test cases, and measured run times.

**Example:** Main Gate → Hospital → Market → Metro Station costs 29 minutes in normal traffic.