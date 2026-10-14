# Shortest-Path Planning in a Large-Scale IoV/UAV Mobility Network

> **Completed implementation:** See [SOLUTION_README.md](SOLUTION_README.md) for setup, design, algorithms, measured results, plots, bonus task, assignment answers, and viva questions. This file preserves the original problem statement.

**Objective:** Study the practical performance of shortest-path algorithms on a realistic large-scale mobility network. Identify a suitable publicly available dataset related to Internet of Vehicles (IoV), vehicular mobility, UAV mobility, road networks, or a similar moving-network scenario; model it as a weighted graph; and analyze shortest-path performance on graphs of different sizes.

---

## Problem Statement

Consider a mobility network represented as a weighted graph:

```
G = (V, E)
```

- **V** represents locations, intersections, waypoints, or mobility nodes.
- **E** represents feasible movements between locations.
- Each edge **(u, v)** has a positive weight **w(u, v)**, representing distance, travel time, or another meaningful movement cost.

Your task is to determine the shortest path between a given source location **S** and destination location **D**.

---

## Part A: Dataset Selection

Identify a suitable **publicly available real-world or realistic dataset** that can be used to formulate the shortest-path problem. It may relate to vehicular mobility/IoV, urban road networks, UAV mobility or waypoints, traffic networks, transportation networks, or another suitable mobility scenario.

The dataset must be sufficiently large to permit meaningful algorithmic performance analysis. Clearly report:

1. dataset name;
2. source or URL;
3. brief description of the dataset;
4. number of records, nodes, and edges used;
5. how the dataset is converted into a graph;
6. what each vertex represents;
7. what each edge represents;
8. what edge weight is used;
9. why the selected dataset is suitable for this problem.

**Choosing and justifying an appropriate dataset is part of the assignment.** Do not use a small manually created graph as the primary dataset.

---

## Part B: Graph Construction

Preprocess the selected dataset and construct the corresponding weighted graph using an **adjacency-list representation**.

After constructing the graph, report:

- number of vertices;
- number of edges;
- average degree;
- maximum degree.

If the original dataset contains additional information that is not required for shortest-path computation, extract only the relevant information needed to construct the graph.

---

## Part C: Dijkstra's Algorithm

Implement **Dijkstra's shortest-path algorithm** using a min-priority queue. For a given source **S** and destination **D**, report:

1. shortest-path cost;
2. complete sequence of vertices in the shortest path;
3. number of vertices explored;
4. number of edges examined;
5. execution time.

Built-in shortest-path implementations from graph-processing libraries are not permitted. Also state and explain the theoretical time complexity of your implementation.

---

## Part D: A* Algorithm

Implement the **A\*** shortest-path algorithm for the same graph. For a vertex *v*, evaluate:

```
f(v) = g(v) + h(v)
```

Here, **g(v)** is the cost from the source to *v*, and **h(v)** is a heuristic estimate of the cost from *v* to the destination.

If positional coordinates are available, an appropriate distance-based heuristic may be used. Justify the selected heuristic and discuss whether it is admissible. Report the same performance metrics as for Dijkstra's algorithm.

---

## Part E: Experimental Evaluation

Perform experiments using multiple graph sizes obtained from the selected dataset. Suggested graph sizes are approximately:

```
1,000 · 5,000 · 10,000 · 25,000 · and, if feasible, 50,000+ vertices
```

For each graph size, use multiple source-destination pairs. Record results in a table similar to the following:

| Graph Size | Algorithm | Shortest-Path Cost | Vertices Explored | Edges Examined | Execution Time |
|------------|-----------|--------------------|-------------------|----------------|----------------|
| —          | Dijkstra  | —                  | —                 | —              | —              |
| —          | A*        | —                  | —                 | —              | —              |

Use at least **five different source-destination pairs** for each selected graph size and report average performance over the selected queries.

---

## Part F: Analysis

| #   | Question |
|-----|----------|
| Q1  | Why is the dataset you selected suitable for shortest-path analysis? |
| Q2  | How did you transform the raw dataset into a weighted graph? |
| Q3  | Do Dijkstra's algorithm and A* produce the same optimal path cost in your experiments? Explain. |
| Q4  | Which algorithm explores fewer vertices, and why? |
| Q5  | How does execution time vary as the graph size increases? |
| Q6  | Explain the effect of the graph's density on shortest-path computation. |
| Q7  | What is the theoretical time complexity of your Dijkstra implementation? |
| Q8  | What heuristic did you use for A*? Is it admissible and/or consistent? Justify your answer. |
| Q9  | What difficulties did you face while converting the real-world dataset into a graph? |
| Q10 | Based on your observations, which algorithm would you recommend for large-scale IoV/UAV route planning? Justify your answer. |

---

## Bonus Task: Dynamic Edge Costs

Real mobility networks are dynamic. Travel cost may change due to congestion, link quality, weather, or other factors. Define an edge cost such as:

```
w(u, v) = αd(u, v) + βc(u, v)
```

- **d(u, v)** represents distance;
- **c(u, v)** represents another dynamic cost such as congestion or delay;
- **α** and **β** are weighting parameters.

Modify selected edge weights and recompute the shortest path. Compare the new route with the original route and discuss the effect of changing network conditions.

---

## Implementation Requirements

1. Students must independently identify a suitable dataset.
2. The selected dataset must be publicly available and properly cited.
3. The graph must be represented using an adjacency list.
4. Dijkstra's algorithm must use a min-priority queue.
5. A* must be implemented independently.
6. Built-in shortest-path implementations are not permitted.
7. Path reconstruction must be implemented explicitly.
8. The implementation must handle disconnected source-destination pairs appropriately.
9. Dataset preprocessing steps must be clearly documented.
10. All experiments must be reproducible.

---

## Submission

Submit the following:

1. source code;
2. dataset source/reference;
3. preprocessing details;
4. README with execution instructions;
5. experimental results;
6. plots comparing the algorithms;
7. a short report containing observations and answers to Part F.

---

> **Important Note**
>
> The objective of this assignment is not merely to execute a shortest-path algorithm. You are expected to make appropriate decisions regarding **dataset selection, graph modelling, algorithm implementation, and performance evaluation**. The quality of these decisions will be considered during evaluation.
