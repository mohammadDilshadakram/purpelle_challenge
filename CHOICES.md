# Engineering Decisions & Trade-offs

This document outlines the core architecture and engineering decisions, technology selections, and trade-offs made during the design and implementation of the **Store Intelligence System** for the **Purplle Tech Challenge 2026**.

---

## 1. Why YOLOv8?

Object detection forms the entry point of our computer vision pipeline. We selected **YOLOv8** (specifically the nano model `yolov8n.pt`) as our primary person detection model.

### Detailed Rationale
*   **Accuracy-to-Speed Ratio**: YOLOv8 offers an outstanding Pareto frontier for real-time edge processing. The nano variant runs comfortably at high frame rates (exceeding 30 FPS on consumer CPU hardware) while retaining a high Mean Average Precision (mAP) for person detection.
*   **Deployment Versatility**: The model natively exports to multiple optimized runtime backends such as ONNX, OpenVINO, TensorRT, and CoreML, allowing seamless transition from CPU-based development to GPU-accelerated production.
*   **Ecosystem & Active Support**: Supported by `ultralytics`, the model benefits from a robust ecosystem, clean developer APIs, pre-trained weights, and active community maintenance.

### Comparative Evaluation

| Model Class | Frame Rate (CPU) | Detection Accuracy (Person) | Edge Deployability | Inference Latency |
| :--- | :--- | :--- | :--- | :--- |
| **YOLOv8 (Nano)** | **High (30+ FPS)** | **High** | **Excellent** | **Low (<15ms)** |
| **Faster R-CNN** | Low (<5 FPS) | Very High | Poor (Heavy) | High (>150ms) |
| **SSD (Single Shot Detector)**| Medium (15 FPS) | Moderate | Good | Moderate (~50ms) |
| **YOLOv5** | High (25 FPS) | Moderate-High | Excellent | Low (~18ms) |

*   **vs. Faster R-CNN**: While Faster R-CNN provides highly detailed two-stage region-proposal detections, its multi-stage design introduces prohibitive latency and GPU requirements that make real-time edge deployments impractical.
*   **vs. SSD**: SSDs are lightweight but frequently struggle with scale-variant detections (e.g., detecting customers far away in the store or occluded in aisles).
*   **vs. YOLOv5**: YOLOv8 utilizes an anchor-free detection head and improved spatial attention blocks, yielding superior detection of overlapping customers in dense zones compared to its predecessor.

### Engineering Trade-offs
*   *Selected Trade-off*: We prioritized inference speed and low resource consumption by choosing the **Nano** variant. 
*   *Alternative Considered*: The **Medium (yolov8m)** or **Large (yolov8l)** models would yield higher bounding-box precision and fewer false negatives for distant shoppers. However, they would drop the pipeline's processing speed below real-time on CPU. Given that our downstream ByteTrack tracker compensates for intermittent detection misses via Kalman filter state predictions, the Nano variant represents the optimal choice.

---

## 2. Why ByteTrack?

Multi-object tracking (MOT) associates detections across frames to track individuals. We selected **ByteTrack** as our tracking engine.

### Detailed Rationale
*   **Stable Tracking in Crowds**: Standard trackers discard low-confidence bounding boxes to avoid noise. ByteTrack's primary innovation lies in its association method: it keeps almost all detection boxes and groups them into high-confidence and low-confidence pools. It utilizes Kalman filters to project trajectories and matches low-confidence boxes (often representing occluded or distant people) to existing tracks.
*   **High ID Retention**: By associating low-confidence detections, ByteTrack drastically reduces track fragmentation and identity switches (ID switches) during cross-customer crossings.
*   **Zero Feature Extraction Overhead**: Unlike DeepSORT, ByteTrack is motion-based rather than appearance-based. It does not run a secondary Re-Identification (Re-ID) neural network to extract visual embeddings, making it extremely fast.

### Comparative Evaluation

| Tracker | Computational Cost | ID Switches in Crowds | Appearance Re-ID Support | Setup Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **ByteTrack** | **Minimal** | **Low** | **No** | **Low** |
| **SORT** | Extremely Low | High | No | Very Low |
| **DeepSORT** | High | Low-Moderate | Yes (CNN embedding) | Moderate |
| **BoT-SORT** | Moderate-High | Very Low | Yes | High |

*   **vs. SORT**: SORT is highly efficient but fails during brief occlusions (e.g., a customer walking behind a structural pillar or another shopper), causing track IDs to reset frequently.
*   **vs. DeepSORT**: DeepSORT runs a deep CNN feature extractor on every cropped bounding box to compute visual vectors. While beneficial for long-term re-identification, it increases computational cost by 2-3x, which degrades performance on edge devices.
*   **vs. BoT-SORT**: BoT-SORT combines camera motion compensation and appearance features. It is highly accurate but computationally heavy and unnecessarily complex for fixed-angle retail CCTV setups.

### Engineering Trade-offs
*   *Selected Trade-off*: We chose a motion-only tracker (ByteTrack). 
*   *Consequence*: If a customer leaves the frame or is fully occluded for an extended period (exceeding the tracking lookback limit), they will be assigned a new ID upon reappearance. However, this is an acceptable trade-off to ensure high-performance, real-time edge capabilities.

---

## 3. Why Virtual Line Crossing?

To measure footfall (entries and exits), we used a geometric virtual line crossing engine rather than complex full-trajectory analysis.

### Detailed Rationale
*   **Simplicity and Determinism**: Bounding box centers are checked against a configured linear equation. This math is fast, reliable, and uses virtually no CPU.
*   **Frictionless Debugging**: Defining a single Y-coordinate threshold or a simple 2D line segment allows store operators to easily map doorway coordinates without complex configuration.

### Comparative Evaluation
*   **vs. Full Trajectory Analysis**: This approach monitors the entire path of a customer across the camera view to classify their behavior. While detailed, it requires complex spatial clustering and is sensitive to track fragmentation (which can split a single path into separate fragments and break classifier logic).
*   **vs. Zone Transition Models**: This method defines multi-polygon regions (e.g., "Outside Zone" and "Inside Zone") and tracks movement between them. While robust, polygon intersections are computationally heavier and require complex configuration compared to a simple horizontal boundary crossing.

### Engineering Trade-offs
*   *Selected Trade-off*: We implemented a line-crossing engine combined with a stateful Finite State Machine (FSM) containing a **dead-zone buffer (hysteresis)** and a **temporal cooldown**.
*   *Benefit*: This design prevents double-counting when a customer stands directly on the threshold. The FSM requires the customer to cross a 20-pixel clearance area before registering an entry or exit, while the cooldown ignores jitter within short intervals.

---

## 4. Why SQLite?

Our backend database stores compiled logs, metrics, timelines, and security anomalies. We chose **SQLite** as the primary datastore.

### Detailed Rationale
*   **Zero-Configuration & Portability**: SQLite is a serverless, single-file relational database. It runs out of the box without requiring the installation of database servers, credential configuration, or network setups, making it ideal for hackathons and edge device deployments.
*   **Low Footprint**: Since our CV pipeline runs locally on the edge, keeping the database in the same container minimizes system overhead and eliminates network latency during writes.
*   **Transaction Safety (ACID)**: Using SQLAlchemy, we gain full ACID transaction safety, enabling structured schema relationships (e.g., link visitor stays to anomalies) and reliable concurrent reads.

### Comparative Evaluation
*   **vs. PostgreSQL**: PostgreSQL is a robust, production-grade relational database. However, it requires a separate service container, network port binding, and database credentials, which increases deployment friction on edge hardware.
*   **vs. MongoDB**: MongoDB is a NoSQL document database. While convenient for saving raw JSON logs, the structured nature of our domain model (e.g., relational anomalies and visitors) benefits from standard SQL queries and validation.

### Engineering Trade-offs
*   *Selected Trade-off*: SQLite handles concurrent write limits (due to database-level locks) by delegating heavy processing to local JSON files. The FastAPI backend syncs changes back to the SQLite file using file modification checks (`mtime`), ensuring smooth execution and preventing database write contention.

---

## 5. Why FastAPI?

The backend web server exposes data to our client-side dashboard. We selected **FastAPI** to build these REST services.

### Detailed Rationale
*   **Asynchronous Processing**: FastAPI's async design allows it to handle concurrent API queries efficiently under low memory conditions.
*   **Pydantic Type Safety**: By using Pydantic V2 schemas, requests and responses are verified at runtime, ensuring robust endpoints and clear error responses.
*   **Automatic Swagger Documentation**: Developers can instantly access interactive API testing interfaces at `/docs` without writing manual OpenAPI YAML files.

### Comparative Evaluation
*   **vs. Flask**: Flask is lightweight but lacks native data validation, async support, and auto-generated documentation. Implementing these features requires multiple third-party libraries, leading to fragmented setups.
*   **vs. Django REST Framework (DRF)**: DRF is full-featured but heavy. Its large ORM layer and configuration overhead are unnecessary for a microservice-style retail analytics edge node.

### Engineering Trade-offs
*   *Selected Trade-off*: While Flask is easier for beginners, FastAPI's schema validation and auto-generated OpenAPI documentation make it the better choice for building secure, robust web APIs.

---

## 6. Why Streamlit?

The user interface must convey real-time retail insights clearly and dynamically. We selected **Streamlit** to build the dashboard.

### Detailed Rationale
*   **Development Speed**: Streamlit lets developers build data dashboards in pure Python, bypassing complex HTML/CSS/JS setups. This is crucial for fast iteration.
*   **Rich Interactive Components**: It offers native integrations with plotting engines like Altair, allowing us to build responsive, interactive charts with minimal code.
*   **Zero State Setup**: Streamlit handles client-server state out of the box, making it easy to create multi-page layouts and configure options like auto-refresh rates.

### Comparative Evaluation
*   **vs. React + FastAPI**: A custom React frontend offers maximum UI flexibility but requires separate state management (e.g., Redux), routing, and bundlers (Vite/Webpack), which would consume significant development time.
*   **vs. Dash**: Dash is powerful for analytics but has a steep learning curve and verbose syntax compared to Streamlit.

### Engineering Trade-offs
*   *Selected Trade-off*: Streamlit reruns the entire Python script on user interaction. 
*   *Mitigation*: To maintain a fast, responsive UI, we fetch all API endpoints once at startup and cache the results. This prevents redundant network requests during page navigation.

---

## 7. Anomaly Detection Design

Retail managers need to monitor operational efficiency and safety. We designed a modular anomaly system around three key events:

### 1. Crowd Formation
*   *Logic*: Triggers when store occupancy exceeds a threshold (e.g., 15 people) for a continuous duration (e.g., 30 seconds).
*   *Business Justification*: Detects customer congestion, checkout bottlenecks, or promotional aisle crowds, helping managers allocate staff effectively.

### 2. Excessive Loitering
*   *Logic*: Triggers when an individual `track_id` remains inside the store longer than a configured threshold (e.g., 15 minutes).
*   *Business Justification*: Helps identify security concerns, customers who may need assistance, or shelf-stocking delays.

### 3. Traffic Spikes
*   *Logic*: Triggers when entry events in a time window exceed the rolling average of previous windows by a set multiplier (e.g., 200%).
*   *Business Justification*: Alerts staff to sudden traffic surges (e.g., tour bus arrivals or peak hours), allowing them to open extra checkout lanes.

---

## 8. Scalability Considerations

The system's architecture is designed to scale from a single prototype to a distributed multi-store platform:

```
+---------------------------------------------------------------------------------+
|                                 CURRENT DESIGN                                  |
|                                                                                 |
|  [CCTV Video File] ---> [YOLOv8 + ByteTrack] ---> [SQLite] ---> [FastAPI / UI]  |
|                                                                                 |
|  * Runs locally on a single machine.                                            |
|  * File-based batch processing.                                                 |
+---------------------------------------------------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|                                 FUTURE DESIGN                                   |
|                                                                                 |
|  [RTSP IP Cams] ---> [GStreamer/DeepStream] ---> [Kafka] ---> [FastAPI Service] |
|                                                               |                 |
|                                                               v                 |
|                                                       [PostgreSQL / Cloud]      |
|                                                                                 |
|  * Real-time streaming over RTSP.                                               |
|  * Distributed ingestion via Apache Kafka.                                      |
|  * Centralized PostgreSQL cloud database.                                       |
+---------------------------------------------------------------------------------+
```

### Transition Roadmap
1.  **Ingestion (Batch ➔ RTSP Stream)**: Replace static video processing with `GStreamer` or NVIDIA `DeepStream` pipelines to ingest RTSP streams from IP cameras.
2.  **Messaging Layer (Local ➔ Kafka)**: Use Apache Kafka as a message broker to stream coordinate records from edge detection nodes to a central processing engine.
3.  **Database (SQLite ➔ PostgreSQL)**: Migrate the database to a cloud-managed PostgreSQL cluster to support concurrent writes from multiple store locations.
4.  **Inference (CPU ➔ TensorRT)**: Export YOLOv8 to TensorRT and run inference on NVIDIA Jetson edge devices to minimize latency.

---

## 9. Challenges Encountered

### 1. Tracking Stability and Occlusions
*   *Challenge*: Shoppers passing behind pillars or overlapping in aisles caused trackers to lose association, resulting in identity resets and inflated visitor counts.
*   *Resolution*: Adjusted ByteTrack's frame lookback buffer to keep inactive track states in memory longer, allowing the system to reassociate IDs when the person reappeared.

### 2. Double Counting at Doorways
*   *Challenge*: Customers loitering near the entrance triggered duplicate entry/exit events as their bounding boxes moved back and forth over the coordinate threshold.
*   *Resolution*: Implemented a stateful hysteresis FSM. The system defines a dead-zone buffer around the line and requires a customer to fully cross this buffer to register an event.

### 3. Database Write Contention
*   *Challenge*: Simultaneous database writes from multiple camera modules caused SQLite lock contentions and slowed down the application.
*   *Resolution*: Decoupled the pipeline by saving intermediate tracking events to local JSON files. The FastAPI backend syncs these changes to SQLite using file modification checks, reducing database write load.

---

## 10. Future Improvements

1.  **Multi-Camera Re-Identification (Re-ID)**: Track shoppers across different camera feeds using appearance-based feature vectors. This prevents resetting customer IDs when they move between camera zones.
2.  **Demographic Analysis**: Integrate lightweight classification models to estimate age and gender groups, providing deeper demographic insights.
3.  **Staff vs. Customer Classification**: Classify individuals by clothing features or entry points to filter out employees and ensure highly accurate customer metrics.
4.  **Predictive Staffing Alerts**: Use historical occupancy trends to forecast traffic spikes, prompting managers to optimize staff schedules in advance.
5.  **Interactive Heatmaps**: Generate 2D density heatmaps overlaid on store floor plans to help managers optimize product placement.
