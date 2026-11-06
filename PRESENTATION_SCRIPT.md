# Live Delivery Tracker: Presentation Script

**Total: about 6 min 35 s**, which leaves about 25 seconds of buffer under the 7-minute limit.
Replace `[Presenter 1]` and `[Presenter 2]` with your names. The same words are in each slide's speaker notes.

| # | Slide | Who | Time | Ends at |
|---|---|---|---|---|
| 1 | Live Delivery Tracker | P1 | 0:15 | 0:15 |
| 2 | "Where is my delivery right now?" | P1 | 0:30 | 0:45 |
| 3 | How the data flows | P1 | 0:35 | 1:20 |
| 4 | AWS IoT Core | P1 | 0:45 | 2:05 |
| 5 | One message, one rule | P1 | 0:30 | 2:35 |
| 6 | Amazon Location Service | P2 | 0:45 | 3:20 |
| 7 | A small distributed system | P2 | 0:35 | 3:55 |
| 8 | **Live demo** | P1 + P2 | 1:30 | 5:25 |
| 9 | What surprised us | P1 | 0:30 | 5:55 |
| 10 | Same pattern, many products | P2 | 0:25 | 6:20 |
| 11 | Thank you | P2 | 0:15 | 6:35 |

**Before you start:** have `dashboard.py` running, http://localhost:8000 open in one tab, and the AWS console's MQTT test client open in another, subscribed to `trucks/location`. Keep the backup video ready to play.

---

### 1. Live Delivery Tracker · P1 · 0:15
> Assalam-o-Alaikum and good morning everyone. We are [Presenter 1] and [Presenter 2]. Today we will show you how to track a delivery truck live on a map, using two AWS services: AWS IoT Core and Amazon Location Service.

### 2. The problem · P1 · 0:30
> Think about the last time you ordered food or booked a ride. The first thing you check is: where is it right now? Behind that little moving icon is a hard problem. Every vehicle has to report its position every few seconds over unreliable mobile networks. Every position has to be stored. And the answer has to be live, for thousands of vehicles at the same time. Building that yourself means servers, databases and a lot of scaling work. We wanted to see how far managed cloud services can take us.

### 3. How the data flows · P1 · 0:35
> Here is what we built. Our truck is a Python program pretending to be a GPS device. Once a second it sends its location to AWS IoT Core. An IoT rule picks up every message and forwards it to an Amazon Location tracker, which stores the truck's position history. Finally, our live map reads that history and draws the route. Notice that no part talks directly to another: each piece only hands data to the cloud. The orange parts are AWS IoT Core, which I will explain. The teal parts are Amazon Location Service, which [Presenter 2] will explain.

### 4. AWS IoT Core · P1 · 0:45
> AWS IoT Core is a managed service that connects devices to the cloud. Four ideas matter here.
> First, every device is registered as a "thing". Ours is truck01, and it has its own X.509 certificate, so it proves who it is without a password.
> Second, devices talk using MQTT, a lightweight publish/subscribe protocol designed for weak mobile networks. A device publishes to a topic; anyone interested subscribes to it.
> Third, a policy says exactly what the device may do. Our truck can only connect as truck01 and publish to one topic, nothing else.
> And fourth, the rules engine: SQL-like rules that react to messages and send them to other AWS services, without us running any servers.

### 5. One message, one rule · P1 · 0:30
> This is the actual message our truck publishes on the topic trucks/location: a device ID, latitude, longitude and a timestamp, in plain JSON.
> Our rule is one line of SQL: select everything from that topic. Its action is Amazon Location: it takes deviceId, latitude and longitude out of each message and writes them into our tracker, DeliveryTracker. If the rule ever fails, the error is republished to a separate topic, errors/trucks, so we can debug it.
> Now [Presenter 2] will show you where the data goes.

### 6. Amazon Location Service · P2 · 0:45
> Amazon Location Service adds maps and location features to applications. We used three of its parts.
> Trackers store each device's position history. We chose distance-based filtering, which ignores moves smaller than 30 metres, so GPS jitter does not waste storage or money.
> Routes calculates real road routes. Our truck follows the road route it gave us from FAST to Faisal Mosque.
> And Maps gives us the map itself, through an API key that is only allowed to load map tiles, and only from our dashboard.
> A fourth feature, geofences, could alert us when the truck enters or leaves an area, like the customer's street. That is our next step.

### 7. A small distributed system · P2 · 0:35
> Why does this belong in a Parallel and Distributed Computing course? Because it is a small distributed system.
> It is decoupled: with publish/subscribe, the truck never knows the tracker exists. We could add a second consumer, like an SMS alert, without touching the truck.
> It is event-driven: every message triggers work, and nothing sits idle in between.
> It runs in parallel at scale: the same setup works for one truck or thousands, each publishing at the same time, and AWS scales out for us.
> And it is reliable: messages use MQTT quality of service 1, meaning at-least-once delivery, over an encrypted TLS connection.

### 8. Live demo · P1 + P2 · 1:30 (switch to the laptop)
> **P2:** Let's see it live. I start our dashboard. This is the map of Islamabad, still empty.
> **P1:** *(runs `py -3.13 truck_simulator.py --mode mqtt`)* And I start truck01. It connects to IoT Core with its certificate. You can see "connected" here.
> **P1** *(switches to the MQTT test client)***:** In the AWS console you can see every message arriving, one per second, with the truck's latitude and longitude.
> **P2** *(switches to the map)***:** And here is the truck leaving FAST. The trail is not drawn from our laptop's memory: the map reads it back from the Amazon Location tracker every two seconds.
> **P2:** The whole trip is about 11 kilometres and takes under three minutes, so we will let it drive while we continue, and come back to it at the end.

*If anything fails, play the backup video and keep talking over it.*

### 9. What surprised us · P1 · 0:30
> Three things surprised us while building this.
> First, our new IoT endpoint address "did not exist" for several minutes. New DNS names take time to spread, and networks even cache the "not found" answer.
> Second, our truck jumped across the map instead of moving smoothly. The tracker's time-based filtering keeps only one position every 30 seconds, so we switched to distance-based filtering.
> And third, permissions. Every piece needed exactly the right policy, which taught us the principle of least privilege the hard way.

### 10. Same pattern, many products · P2 · 0:25
> The same pattern powers products you use every day: ride-hailing apps, food and parcel delivery, fleet and asset tracking, and school-bus tracking.
> And the cost for us was zero out of pocket. IoT Core is billed per million messages, and one demo trip sends about 150. Everything was covered by AWS Free Tier credits, and we set a zero-spend budget, so AWS emails us if anything ever starts costing money.

### 11. Thank you · P2 · 0:15 (switch back to the map first)
> And our truck has just arrived at Faisal Mosque.
> To sum up: AWS IoT Core gets device data into the cloud securely, and Amazon Location Service turns it into places on a map. Together, with no servers of our own, they make a live tracking system.
> Thank you. We are happy to take your questions.

---

**Likely questions:**
- *What if the truck loses its connection?* MQTT with QoS 1 resends messages that weren't acknowledged, and a real device would buffer positions and send them when it reconnects.
- *Why not just send GPS straight to a database?* IoT Core handles device identity, encryption and millions of connections, and the rules engine lets you add new consumers without changing the device.
- *Could this track many trucks?* Yes. Each truck gets its own thing and certificate and uses a different `deviceId`; the tracker stores each one's history separately.
