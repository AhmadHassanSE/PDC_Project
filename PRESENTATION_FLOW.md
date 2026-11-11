# Live Delivery Tracker: Presentation Flow for Two Presenters

Deck: `Live Delivery Tracker - Fleet Presentation.pptx` (17 slides). The words for every slide are also in its speaker notes.

Replace `[Presenter 1]` and `[Presenter 2]` with your names. **P1 owns AWS IoT Core** (orange label on a slide). **P2 owns Amazon Location Service** (teal label).

## The whole session at a glance

| Part | What happens | Who | Time |
|---|---|---|---|
| 1 | Slides 1 to 15: the ideas | P1 and P2 | about 11 min 30 s |
| 2 | AWS console: how each piece is set up | P1 and P2 | about 8 min |
| 3 | Live demo (slide 16, then the laptop) | P1 and P2 | about 5 min |
| 4 | Slide 17: wrap-up and questions | P2 | 0:30 plus questions |

About 25 minutes in total. If you are short of time, cut console step 2b (the rule's role) and step 4's "create access key" walkthrough.

## Before you start

- [ ] `demo\aws_credentials` holds a working access key. **Never open this file, or `certs\truck01.private.key`, on the projector.**
- [ ] Terminal 1: `cd demo` then `py dashboard.py`. Leave it running. Open http://localhost:8000 in a browser tab.
- [ ] Terminal 2: `cd demo`, with `py truck_simulator.py --mode mqtt` typed but **not** run.
- [ ] AWS console signed in, region **N. Virginia (us-east-1)**, with these tabs open in this order:
  1. Amazon Location, Trackers: https://us-east-1.console.aws.amazon.com/location/tracking/home?region=us-east-1#/
  2. IoT Core, Rules: https://us-east-1.console.aws.amazon.com/iot/home?region=us-east-1#/rulehub
  3. IoT Core, Things: https://us-east-1.console.aws.amazon.com/iot/home?region=us-east-1#/thinghub
  4. IAM, Users: https://us-east-1.console.aws.amazon.com/iam/home#/users
  5. IoT Core, MQTT test client: https://us-east-1.console.aws.amazon.com/iot/home?region=us-east-1#/test
- [ ] Browser zoom at 125% or more so the back row can read the console.
- [ ] Backup: `Demo_video_PDC.mp4` ready to play if the Wi-Fi fails.

---

## Part 1: Slides (about 11 min 30 s)

| # | Slide | Who | Time | Ends at |
|---|---|---|---|---|
| 1 | Live Delivery Tracker | P1 | 0:20 | 0:20 |
| 2 | Where is my delivery right now? | P1 | 0:45 | 1:05 |
| 3 | Four trucks, one live map | P2 | 0:40 | 1:45 |
| 4 | How the data flows | P1 | 1:00 | 2:45 |
| 5 | Every device proves who it is | P1 | 0:55 | 3:40 |
| 6 | MQTT: publish and subscribe | P1 | 0:55 | 4:35 |
| 7 | One message, one rule | P1 | 0:50 | 5:25 |
| 8 | Positions in, places out | P2 | 0:55 | 6:20 |
| 9 | Which positions are worth keeping? | P2 | 0:45 | 7:05 |
| 10 | From one truck to a fleet | P2 | 0:50 | 7:55 |
| 11 | Three identities, three small policies | P1 | 0:55 | 8:50 |
| 12 | A small distributed system | P2 | 0:50 | 9:40 |
| 13 | What surprised us | P1 | 0:40 | 10:20 |
| 14 | Same pattern, many products | P2 | 0:40 | 11:00 |
| 15 | Building it, step by step | P1 | 0:30 | 11:30 |

Hand-overs: P1 to P2 after slide 2, back to P1 for slide 4, P1 to P2 after slide 7 ("Now [Presenter 2] will show you where the data goes"), then alternating from slide 11.

---

## Part 2: The AWS console (about 8 min)

Everything already exists in the account, so for each piece: **open the existing resource, point at the settings that matter, then open the Create form to show where they are chosen, and cancel.** Nothing is created live, so nothing can break before the demo.

Start by pointing at the region selector (top right): "Everything we show is in one region, N. Virginia. A wrong region is the most common reason this fails."

### Step 1. The tracker (P2, about 1:15)

Tab 1: **Amazon Location > Trackers > DeliveryTracker**.

Show:
- **Name:** `DeliveryTracker`
- **Position filtering:** `Distance-based`

Then click **Create tracker** to show the form, point at the **Position filtering** choice (Time-based, Distance-based, Accuracy-based), and click **Cancel**.

> This tracker is the whole database of our project. We gave it a name and chose one setting: distance-based filtering, which ignores moves under 30 metres. No tables, no schema, no server. One tracker stores every truck, each under its own device ID.

### Step 2. The IoT rule (P1, about 2:00)

Tab 2: **IoT Core > Message routing > Rules > truck_location_rule**.

Show:
- **SQL statement:** `SELECT * FROM 'trucks/location'`
- **Action: Location**, with these fields:

| Field | Value |
|---|---|
| Tracker name | `DeliveryTracker` |
| Device ID | `${deviceId}` |
| Latitude | `${latitude}` |
| Longitude | `${longitude}` |
| Timestamp value | `${timestamp()}` |
| Timestamp unit | `MILLISECONDS` |
| IAM role | `iot-location-role` |

- **Error action:** republish to topic `errors/trucks`

> This rule is the glue. The SQL chooses which messages it cares about: everything on trucks/location. The action says what to do with each one: write it into the tracker. The values in dollar-braces are filled in from each message, so truck02's message is stored under truck02. That is why adding more trucks needed no change here.

**Step 2b. The rule's role (P1).** Click the role name `iot-location-role` (it opens in IAM), then open its policy. It should look like this:

```json
{
  "Version": "2012-10-17",
  "Statement": {
    "Effect": "Allow",
    "Action": "geo:BatchUpdateDevicePosition",
    "Resource": "arn:aws:geo:us-east-1:ACCOUNT_ID:tracker/DeliveryTracker"
  }
}
```

> The rule runs as this role. It can do exactly one thing: write positions into this one tracker. The console wrote this policy for us when we clicked "Create new role".

### Step 3. The thing, its certificate and its policy (P1, about 2:00)

Tab 3: **IoT Core > Manage > All devices > Things > truck01**.

1. Show the thing `truck01`. Open its **Certificates** tab and click the certificate: status **Active**.
2. On the certificate page, open **Policies** and click `truck01-policy`. Show the JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:us-east-1:ACCOUNT_ID:client/truck01"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": "arn:aws:iot:us-east-1:ACCOUNT_ID:topic/trucks/location"
    }
  ]
}
```

3. Go back to **Things**, click **Create things > Create single thing**, and step through the wizard to the certificate page: **Auto-generate a new certificate**. Point out that the next page offers the downloads once only. Click **Cancel**.
4. In VS Code, show the **file names** in `demo\certs\` (do not open the private key).

> A thing is the device's identity card. The certificate proves it is truck01, and the policy on that certificate allows two actions only: connect with the client ID truck01, and publish to trucks/location. It cannot subscribe, and it cannot touch any other topic. The private key can be downloaded once, when the certificate is made. If you lose it, you make a new certificate.

### Step 4. The IAM user for our laptop (P2, about 1:30)

Tab 4: **IAM > Users > pdc-demo-user > Permissions**. Expand the inline policy and show the JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "FindIotEndpoint",
      "Effect": "Allow",
      "Action": "iot:DescribeEndpoint",
      "Resource": "*"
    },
    {
      "Sid": "PublishTruckPositions",
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": "arn:aws:iot:us-east-1:ACCOUNT_ID:topic/trucks/location"
    },
    {
      "Sid": "ReadAndResetTracker",
      "Effect": "Allow",
      "Action": [
        "geo:GetDevicePositionHistory",
        "geo:BatchDeleteDevicePositionHistory"
      ],
      "Resource": "arn:aws:geo:us-east-1:ACCOUNT_ID:tracker/DeliveryTracker"
    },
    {
      "Sid": "CalculateRoadRoute",
      "Effect": "Allow",
      "Action": "geo-routes:CalculateRoutes",
      "Resource": "*"
    }
  ]
}
```

Then open **Security credentials** and point at the **Access keys** section (the key ID is fine to show; the secret is never shown again after creation).

> Our Python scripts are not a device, so they sign in as this IAM user instead. Four statements, one per job: find the IoT endpoint, publish to our one topic, read and reset our one tracker, and ask for road routes. The user has no console password and nothing else in the account. Its access key sits in a file next to the scripts, which git ignores. We did not use the AWS CLI at all.

### Step 5. Test the pipeline by hand (P1 publishes, P2 watches the map, about 1:15)

Tab 5: **IoT Core > MQTT test client**.

1. **Subscribe to a topic:** `trucks/location`. Click **Subscribe**. Subscribe to `errors/trucks` too.
2. **Publish to a topic:** topic `trucks/location`, message:

```json
{"deviceId": "truck01", "latitude": 33.6563, "longitude": 73.0153}
```

3. Click **Publish**. The message appears in the subscription.
4. P2 switches to the map tab: **truck01 has appeared at the depot**, and its row says "On the road".

> **P1:** No code has run yet. I am publishing one message by hand, pretending to be truck01.
> **P2:** And there it is on our map. That one message went through IoT Core, through the rule, into the tracker, and our page read it back. The whole pipeline works before we write a line of Python.

Leave the MQTT test client subscribed. You need it in the demo.

---

## Part 3: Live demo (about 5 min)

Show slide 16 for ten seconds ("this is what to watch"), then switch to the laptop.

| Step | Who | Do | Say |
|---|---|---|---|
| 1 | P2 | Show the map at http://localhost:8000 | "This is our dashboard. Four trucks are loaded and waiting at FAST." |
| 2 | P1 | In terminal 2, run `py truck_simulator.py --mode mqtt` | "One command starts the fleet. It clears the old trips, asks Amazon Location for four road routes, then connects to IoT Core over MQTT with the certificate you just saw." Point at `MQTT connect result: Success`. |
| 3 | P1 | Switch to the MQTT test client | "Every message is arriving here, one per truck per second. You can see the different device IDs." |
| 4 | P2 | Switch to the map | "The trucks leave six seconds apart. Each trail is read back from the tracker every two seconds; nothing is drawn from the laptop's memory." |
| 5 | P2 | Untick truck01, truck02 and truck04 | "By default we track all of them. If I only care about one, I untick the rest, and the map follows that truck." |
| 6 | P2 | Click **Track all**, then click **truck02** | "Clicking a truck opens its delivery sheet: where it is going, who receives it, the driver, when it is due, and exactly what it carries. This one is medical supplies that must stay cold." Scroll to the live position feed. |
| 7 | P1 | Click truck03 on the map | "truck03 has the longest trip, 22 kilometres to Saddar. Kilometres driven and positions stored are counting up live." |
| 8 | P2 | Wait for a "Delivered" status (truck02 arrives first, after about 2 minutes) | "And truck02 has delivered." Go to slide 17. |

One honest detail to mention if asked: in `--mode mqtt` a single connection, signed in as truck01, relays all four trucks. In a real fleet each truck would have its own thing, certificate and policy.

**If something fails**

| Problem | What to do |
|---|---|
| MQTT cannot connect | Run `py truck_simulator.py` (no `--mode mqtt`). It publishes over HTTPS with the IAM user instead. |
| The map shows "Can't read the tracker" | Check terminal 1 is still running `py dashboard.py`. Restart it and reload the page. |
| No internet | Play `Demo_video_PDC.mp4` and talk over it. |
| Messages arrive but the map stays empty | Look at `errors/trucks` in the MQTT test client: the rule is failing, usually a region or role problem. |

---

## Part 4: Wrap-up (slide 17, P2)

Switch back to the map first so the finished trips are on screen, then show slide 17 and take questions.

**Likely questions**

- *What if a truck loses its connection?* MQTT with QoS 1 resends messages that were not acknowledged, and a real device would buffer positions and send them when it reconnects.
- *Why not send GPS straight to a database?* IoT Core handles device identity, encryption and millions of connections, and the rules engine lets you add new consumers without changing the device.
- *How does it tell the trucks apart?* By the `deviceId` in each message. The tracker keeps a separate history for each ID.
- *Where does the cargo information come from?* From the delivery sheet in `config.py`. A truck only reports its position; what it carries is dispatch data, which the dashboard joins to the live position by device ID.
- *Would this work for 4,000 trucks?* The AWS side would not change. We would give each truck its own certificate, and the dashboard would need paging and clustering on the map.
- *What did it cost?* Nothing out of pocket. A fleet run is about 640 messages on services billed per million messages and per thousand stored positions.

---

## Full script, slide by slide

### Slide 1. Live Delivery Tracker (P1, 0:20)
> Assalam-o-Alaikum and good morning everyone. We are [Presenter 1] and [Presenter 2]. Today we will show you how to track a whole fleet of delivery trucks live on a map, using two AWS services: AWS IoT Core and Amazon Location Service. First the ideas, then we build it in the AWS console in front of you, then we run it.

### Slide 2. Where is my delivery right now? (P1, 0:45)
> Think about the last time you ordered food or booked a ride. The first thing you check is: where is it right now? Behind that little moving icon is a hard problem. Every vehicle has to report its position every few seconds over unreliable mobile networks. Every position has to be stored. And the answer has to be live, for thousands of vehicles at the same time. Building that yourself means servers, databases and a lot of scaling work. We wanted to see how far managed cloud services can take us.

### Slide 3. Four trucks, one live map (P2, 0:40)
> This is what we built, and you will see it running at the end. Four delivery trucks leave FAST-NUCES for four places in Islamabad and Rawalpindi. Each truck reports its position once a second. One tracker in the cloud stores every position. And this map draws all of them live. We can tick which trucks to follow, and open any truck to see its driver, its delivery and exactly what it is carrying. We run no servers of our own for the tracking: only this small page on a laptop.

### Slide 4. How the data flows (P1, 1:00)
> Here is the whole system. Our trucks are a Python program pretending to be GPS devices. Once a second each truck sends its location to AWS IoT Core, on a topic called trucks/location. An IoT rule picks up every message and forwards it to an Amazon Location tracker, which stores each truck's position history. Finally the live map reads that history every two seconds and draws the routes. Notice that no part talks directly to another: the truck does not know the tracker exists, and the map never hears from a truck. Each piece only hands data to the cloud. The orange parts are AWS IoT Core, which I will explain. The teal parts are Amazon Location Service, which [Presenter 2] will explain.

### Slide 5. Every device proves who it is (P1, 0:55)
> AWS IoT Core is a managed service that connects devices to the cloud. It starts with identity. Every device is registered as a 'thing'. Ours is truck01. The thing gets its own X.509 certificate, so it proves who it is without any password. The private key stays on the device and never leaves it. Then a device policy is attached to the certificate, and it says exactly what this device may do. On the right are the three files a real device carries: its certificate, its private key, and Amazon's root certificate so the device can check it is really talking to AWS. We will create all of this in the console in a few minutes.

### Slide 6. MQTT: publish and subscribe (P1, 0:55)
> Devices talk to IoT Core using MQTT, a lightweight publish/subscribe protocol designed for weak mobile networks. It works like a notice board. A device publishes a message to a topic, here trucks/location. It does not send it to anyone in particular. Anyone interested subscribes to that topic and receives a copy. Today there are two subscribers: our IoT rule, and the MQTT test client in the console that we will use to watch messages arrive. Three details matter. The header is tiny, so it suits slow networks. We use quality of service 1, which means at-least-once delivery: an unacknowledged message is sent again. And everything travels over TLS on port 8883.

### Slide 7. One message, one rule (P1, 0:50)
> This is the actual message a truck publishes: a device ID, latitude, longitude and a timestamp, in plain JSON. On the right is our rule. It is one line of SQL: select everything from the topic trucks/location. Its action is Amazon Location. It takes deviceId, latitude and longitude out of each message and writes them into our tracker, DeliveryTracker. The dollar-and-braces values are substitution templates: IoT Core fills them in from each message. If the rule ever fails, the error is republished to a separate topic, errors/trucks, so we can debug it. Now [Presenter 2] will show you where the data goes.

### Slide 8. Positions in, places out (P2, 0:55)
> Amazon Location Service adds maps and location features to applications. We used three of its parts. Trackers store each device's position history. One tracker holds many devices, and each device's history is kept separately under its device ID. Routes calculates real road routes. Every truck asks it for the road route from FAST to its destination, so the trucks follow real roads instead of straight lines. And Maps can supply the map itself, through an API key that is only allowed to load map tiles, and only from our dashboard. A fourth feature, geofences, could alert us when a truck enters or leaves an area, like the customer's street. That is our next step.

### Slide 9. Which positions are worth keeping? (P2, 0:45)
> A tracker does not have to store every position it receives. You choose a filter when you create it. Time-based filtering keeps one position per device every 30 seconds. We tried that first, and our truck jumped across the map. Distance-based filtering ignores any move shorter than 30 metres. That removes GPS jitter from a parked vehicle, and it costs less, because you pay per stored position. Our trucks move 80 metres per update, so every update is kept and the trail is smooth. This one setting is the difference between a broken demo and a working one.

### Slide 10. From one truck to a fleet (P2, 0:50)
> Our first version tracked one truck. Going to four needed no change at all in AWS. Every truck publishes to the same topic, passes through the same rule, and lands in the same tracker. The only thing that differs is the deviceId inside the message, and the tracker keeps a separate history for each ID. On our side, the simulator runs one thread per truck, so the trucks report independently, the way real devices would. And the dashboard reads the four histories in parallel. The cargo and delivery details you see here are the delivery sheet for each truck, which the map shows next to its live position.

### Slide 11. Three identities, three small policies (P1, 0:55)
> Three different identities touch this system, and each one gets the smallest policy that works. That is the principle of least privilege. The truck, through its certificate, may connect only as truck01 and publish only to trucks/location. It cannot subscribe, and it cannot read anything. Our laptop, as the IAM user pdc-demo-user, may find the IoT endpoint, publish to that one topic, read and reset that one tracker, and calculate routes. Nothing else in the account. And the IoT rule runs with its own role, which may only write positions into that one tracker. If any one of these is stolen, the damage stops there. We will show you each policy in the console.

### Slide 12. A small distributed system (P2, 0:50)
> Why does this belong in a Parallel and Distributed Computing course? Because it is a small distributed system. It is decoupled: with publish/subscribe, a truck never knows the tracker exists. We could add a second consumer, like an SMS alert, without touching the trucks. It is event-driven: every message triggers work, and nothing sits idle in between. It runs in parallel: four trucks publish at the same time from four threads, and the same setup works for four thousand, because AWS scales out for us. And it is reliable: messages use MQTT quality of service 1, at-least-once delivery, over an encrypted connection.

### Slide 13. What surprised us (P1, 0:40)
> Three things surprised us while building this. First, our new IoT endpoint address did not exist for several minutes. New DNS names take time to spread, and networks even cache the 'not found' answer. Second, our truck jumped across the map instead of moving smoothly, which was the time-based filter [Presenter 2] explained. And third, permissions. Every piece needed exactly the right policy, and one wrong account ID in an ARN gives you 'access denied' with very little explanation. That taught us least privilege the hard way.

### Slide 14. Same pattern, many products (P2, 0:40)
> What did this cost? One full run of the fleet sends about 640 messages. IoT Core is billed per million messages, and the tracker per thousand stored positions, so a run costs a small fraction of a cent. Everything was covered by AWS Free Tier credits, and we set a zero-spend budget, so AWS emails us if anything ever starts costing money. And the same pattern powers products you use every day: ride-hailing apps, food and parcel delivery, fleet and asset tracking, and school-bus tracking.

### Slide 15. Building it, step by step (P1, 0:30)
> That is the theory. Now we will switch to the AWS console and show you how each piece is set up, in this order. [Presenter 2] creates the tracker. I create the IoT rule, then the thing with its certificate and policy. [Presenter 2] shows the IAM user and its policy. Then we test the pipeline by hand in the MQTT test client, before any code runs. Everything is in one region, us-east-1. After that, the live demo. (Switch to the browser now. The step-by-step is in PRESENTATION_FLOW.md.)

### Slide 16. Four trucks leave FAST (P2 and P1, 5 minutes)
> P2: The dashboard is running; this is the map, with four trucks waiting at the depot. P1: I start the fleet with one command. It asks Amazon Location for four road routes, then the trucks leave six seconds apart. P1 switches to the MQTT test client: every message is arriving on trucks/location. P2 on the map: all four are tracked by default. Untick trucks to follow just one. Click a truck to open its delivery sheet: driver, due time, cargo, and the live position feed. The full step list is in PRESENTATION_FLOW.md. If anything fails, play Demo_video_PDC.mp4 and keep talking over it.

### Slide 17. Thank you (P2, 0:30)
> And our trucks have arrived. To sum up: AWS IoT Core gets device data into the cloud securely, and Amazon Location Service turns it into places on a map. Together, with no servers of our own, they make a live tracking system for one truck or a whole fleet. Thank you. We are happy to take your questions.
