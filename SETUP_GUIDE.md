# Live Delivery Tracker: Setup Guide
**Amazon Location Service + AWS IoT Core**

A simulated delivery truck drives from FAST-NUCES Islamabad to Faisal Mosque. Every second it sends its GPS position to AWS IoT Core. An IoT rule passes each position to an Amazon Location tracker, and a live map in your browser shows the truck moving.

```
 truck_simulator.py ──MQTT/HTTPS──▶ AWS IoT Core ──IoT rule──▶ Amazon Location tracker
   (fake GPS truck)                  topic: trucks/location        "DeliveryTracker"
                                                                         │
                     browser: http://localhost:8000 ◀── dashboard.py ◀───┘
```

**Time needed:** about 1.5–2 hours the first time.
**Cost:** a few cents at most, and new AWS accounts get free-tier credits to cover it. Part A sets an alert so nothing surprises you.

**Files in the `demo` folder:**

| File | What it does |
|---|---|
| `config.py` | Settings: region, names, start and end points of the route |
| `truck_simulator.py` | The fake truck. Gets a real road route from Amazon Location and sends positions to IoT Core |
| `dashboard.py` | Live map. Reads the tracker and draws the route |
| `policies/iam-user-policy.json` | Permissions for your laptop (pasted in Part D) |
| `policies/iot-device-policy.json` | Permissions for the IoT "thing" (pasted in Part C) |
| `requirements.txt` | Python libraries to install |

> **Use the same region for everything: `us-east-1` (N. Virginia).** Check the region selector at the top-right of the AWS console on every page. A wrong region is the most common reason this demo fails.

---

## Part A: AWS account and cost safety

**A1. Create or sign in to your AWS account.**
- Sign up: https://aws.amazon.com/free/
- Console: https://console.aws.amazon.com/

**A2. Set a "Zero spend" budget, so AWS emails you if anything ever costs money.**
1. Open https://console.aws.amazon.com/billing/home#/budgets
2. Click **Create budget**, choose **Use a template**, then **Zero spend budget**.
3. Enter your email and click **Create budget**.

**A3. Find your 12-digit Account ID.**
Click your account name at the top-right of the console and copy the **Account ID** (for example `123456789012`). You'll paste it into two policies later, in place of `ACCOUNT_ID`.

---

## Part B: Amazon Location Service (the tracker)

**B1. Create the tracker.**
1. Open https://us-east-1.console.aws.amazon.com/location/home?region=us-east-1
2. In the left menu, click **Trackers**, then **Create tracker**.
3. Fill in:
   - **Name:** `DeliveryTracker`
   - **Position filtering:** **Distance-based filtering**
     (do **not** use Time-based: it stores only one position every 30 seconds, so the truck would jump instead of moving smoothly)
   - Leave everything else as default. You don't need a geofence collection or EventBridge.
4. Click **Create tracker**.

> **For your slides:** distance-based filtering ignores movements under 30 m. That removes GPS "jitter" and lowers cost, which is why our simulator moves the truck 80 m per update.

---

## Part C: AWS IoT Core (topic, rule, and the "thing")

Open IoT Core: https://us-east-1.console.aws.amazon.com/iot/home?region=us-east-1

**C1. Create the rule that forwards positions to the tracker.**
1. In the left menu: **Message routing → Rules → Create rule**.
2. **Rule name:** `truck_location_rule` (use underscores only, because hyphens aren't allowed). Click **Next**.
3. **SQL version:** `2016-03-23`. **SQL statement:** paste
   ```sql
   SELECT * FROM 'trucks/location'
   ```
   Click **Next**.
4. **Rule actions → Action 1:** choose **Location** (sends a message to an Amazon Location tracker). Fill in:

   | Field | Value |
   |---|---|
   | Tracker name | `DeliveryTracker` |
   | Device ID | `${deviceId}` |
   | Latitude | `${latitude}` |
   | Longitude | `${longitude}` |
   | Timestamp value | `${timestamp()}` |
   | Timestamp unit | `MILLISECONDS` |
   | IAM role | Click **Create new role**, name it `iot-location-role`, and click **Create** |

5. *(Optional, for debugging.)* Under **Error action**, add **Republish to an AWS IoT topic** with topic `errors/trucks`, using the same role. If the rule fails, the reason will appear on that topic.
6. Click **Next**, then **Create**.

**C2. Test the pipeline by hand, with no code yet.**
1. Left menu: **MQTT test client**.
2. Under **Subscribe to a topic**, enter `trucks/location` and click **Subscribe**. Also subscribe to `errors/trucks` if you added the error action.
3. Under **Publish to a topic**, set the topic to `trucks/location` and paste this message:
   ```json
   {"deviceId": "truck01", "latitude": 33.6563, "longitude": 73.0153}
   ```
   Click **Publish**. The message should appear in the subscription list.
4. Check that it reached the tracker using **CloudShell**, a free terminal in the browser that's already logged in:
   https://us-east-1.console.aws.amazon.com/cloudshell/home?region=us-east-1
   ```bash
   aws location get-device-position-history --tracker-name DeliveryTracker --device-id truck01 --region us-east-1
   ```
   You should see your position under `DevicePositions`. If it's empty, wait 10 seconds and try again. If it's still empty, see **Part G**.

**C3. Register the truck as an IoT "thing" with a certificate.**
This is how real devices connect. It's needed for `--mode mqtt` and gives you something good to show on screen.

1. First create the device policy. Go to **Security → Policies → Create policy**.
   - **Name:** `truck01-policy`
   - Click the **JSON** tab and paste the following, replacing `ACCOUNT_ID` (2 places) with your Account ID from A3:
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
   - Click **Create**.
2. Go to **Manage → All devices → Things → Create things → Create single thing → Next**.
3. **Thing name:** `truck01`. Choose **No shadow**, then click **Next**.
4. Choose **Auto-generate a new certificate (recommended)** and click **Next**.
5. Tick **truck01-policy**, then click **Create thing**.
6. **Download the files now. The private key can't be downloaded again later.**
   - Device certificate (`…-certificate.pem.crt`)
   - Private key file (`…-private.pem.key`)
   - Amazon Root CA 1 (`AmazonRootCA1.pem`). If the link is missing, use https://www.amazontrust.com/repository/AmazonRootCA1.pem
7. Create the folder `C:\Users\DELL\Desktop\PDC_Presentation\demo\certs\`, then move and **rename** the files:
   - `…-certificate.pem.crt` → `certs\truck01.cert.pem`
   - `…-private.pem.key` → `certs\truck01.private.key`
   - `AmazonRootCA1.pem` → `certs\AmazonRootCA1.pem`

> Never share or upload the private key, for example to WhatsApp or GitHub.

---

## Part D: Set up your laptop (Windows)

**D1. Install Python 3.12.**
- Download: https://www.python.org/downloads/windows/ (during setup, **tick "Add python.exe to PATH"**)
- Or, in PowerShell: `winget install -e --id Python.Python.3.12`

**D2. (Optional) Install the AWS CLI.** The demo doesn't need it; it is only handy for checking things by hand.
- Download: https://awscli.amazonaws.com/AWSCLIV2.msi
- Or, in PowerShell: `winget install -e --id Amazon.AWSCLI`

Close and reopen your terminal (in VS Code, open a new terminal), then check that both installed:
```powershell
py --version
aws --version
```

**D3. Create an IAM user with only the permissions the demo needs.**
1. Open https://console.aws.amazon.com/iam/home#/users and click **Create user**.
2. **User name:** `pdc-demo-user`. Don't give it console access. Click **Next**, **Next**, then **Create user**.
3. Open the user, go to **Permissions → Add permissions → Create inline policy**, and click the **JSON** tab.
4. Paste the following, replacing `ACCOUNT_ID` (2 places):
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
5. Click **Next**, name it `pdc-demo-policy`, and click **Create policy**.
6. Go to **Security credentials → Create access key → Command Line Interface (CLI)**. Tick the confirmation box, click **Next**, then **Create access key**. **Download the .csv file.**

**D4. Give the scripts that user's access key.**
The scripts read the key from a file, so you don't need `aws configure`. Create `demo\aws_credentials` (no file extension) with this content, using the values from the .csv:
```
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```
`.gitignore` keeps this file out of git. Never commit or share it.

**D5. Install the Python libraries.**
```powershell
cd C:\Users\DELL\Desktop\PDC_Presentation\demo
py -m pip install -r requirements.txt
```

**D6. Check the route in `config.py`.**
`START` is set to FAST-NUCES Islamabad (H-11/4) and `END` to Faisal Mosque. To confirm or change a point, right-click the place in Google Maps, click the numbers at the top of the menu to copy them, and paste them as `(latitude, longitude)`.

---

## Part E: Run the demo

You need **two terminals**. In VS Code, click the **+** in the terminal panel to open a second one.

**Terminal 1: start the map.**
```powershell
cd C:\Users\DELL\Desktop\PDC_Presentation\demo
py dashboard.py
```
Open **http://localhost:8000** in your browser.

**Terminal 2: start the trucks.**
```powershell
cd C:\Users\DELL\Desktop\PDC_Presentation\demo
py truck_simulator.py
```
The script clears the previous trips, asks **Amazon Location Routes** for a road route for each of the four trucks in `config.FLEET`, and sends one position per truck per second. The trucks leave a few seconds apart, each drawing a trail in its own colour. The longest trip takes about 5 minutes.

On the map, every truck is tracked by default. Untick a truck in the fleet list to hide it, and click a truck to see its delivery sheet: driver, due time, cargo and live positions. To change the trucks, their destinations or their cargo, edit `FLEET` in `config.py`.

**To show a real IoT device connection** (using the certificate from C3):
```powershell
py truck_simulator.py --mode mqtt
```
This opens one MQTT connection as `truck01` and relays all four trucks through it. In a real fleet every truck would have its own thing and certificate.

**Optional extras during the demo:**
- In the IoT console's **MQTT test client**, subscribe to `trucks/location` to show messages arriving live.
- In CloudShell, run the `get-device-position-history` command from C2 to show the raw stored positions.

---

## Part F (optional): Use Amazon's own map instead of OpenStreetMap

This lets you say "even the map tiles come from Amazon Location Service."
1. Open https://us-east-1.console.aws.amazon.com/location/home?region=us-east-1 and go to **API keys → Create API key**.
2. **Name:** `pdc-map-key`. Under **Maps**, allow **GetTile** (and **GetStaticMap** if it's listed).
3. **Referers:** `http://localhost:8000/*`. Set an expiry date after your presentation, then click **Create**.
4. Copy the key value into `config.py`:
   ```python
   MAP_API_KEY = "v1.public.xxxxxxxx..."
   ```
5. Restart `dashboard.py` and refresh the browser.

If the map goes blank, set `MAP_API_KEY = ""` again to switch back to OpenStreetMap.

---

## Part G: Troubleshooting

| Problem | Fix |
|---|---|
| `py` or `aws` is not recognized | Close and reopen the terminal. Reinstall Python with "Add to PATH" ticked |
| `Unable to locate credentials` | Check that `demo\aws_credentials` exists and holds the access key (D4) |
| `AccessDeniedException` / `not authorized` | `ACCOUNT_ID` wasn't replaced in the policy, or a resource is in a different region than `us-east-1` |
| `ResourceNotFoundException` for the tracker | The tracker name must be exactly `DeliveryTracker`, in `us-east-1` |
| Simulator says "Could not get a road route" | The demo still works, but the truck moves in a straight line. Check the `geo-routes:CalculateRoutes` permission and run `py -m pip install -U boto3` |
| Messages appear in the MQTT client but the map stays empty | The rule isn't delivering. Check the rule's field names (`${deviceId}`, …, case-sensitive) and look at `errors/trucks` in the MQTT test client |
| The truck jumps instead of moving smoothly | The tracker uses Time-based filtering. Create a new tracker with Distance-based filtering |
| `--mode mqtt` can't connect | Check the three files in `certs\` and their names, that `truck01-policy` is attached to the certificate, and that `ACCOUNT_ID` is replaced |
| `getaddrinfo failed` / `Could not connect to the endpoint URL` for `…-ats.iot.us-east-1.amazonaws.com` | A brand-new account's IoT endpoint can take up to ~15 min to work on your network. Run `ipconfig /flushdns` and try again later |
| `Using the login credential provider requires…botocore[crt]` | Run `py -m pip install "botocore[crt]"` (needed when you signed in with `aws login`) |
| Scripts hang or say the sign-in expired | Run `aws login --region us-east-1` again |
| Port 8000 already in use | Close the other `dashboard.py` window, or change `PORT` in `dashboard.py` |

---

## Part H: Presentation-day checklist

- [ ] Run the full demo at least twice on the laptop you'll present from.
- [ ] Have a **backup screen recording** in case the venue Wi-Fi fails. Use Windows key + Alt + R (Xbox Game Bar) or OBS.
- [ ] Before you go on stage, start `dashboard.py` and open the browser tab. Start the simulator live, in front of the audience.
- [ ] Keep the IoT console's MQTT test client open in another tab.

**Suggested split for two presenters:**
- **Presenter 1, AWS IoT Core:** what IoT is, MQTT and topics, devices and certificates (show `truck01` and its policy), and the rules engine (show `truck_location_rule`).
- **Presenter 2, Amazon Location Service:** trackers and position filtering, routes (the truck follows real roads), maps, and real-world uses such as ride-hailing apps, food delivery and fleet tracking.

---

## Part I: Clean up after the presentation

Delete these in the console (all in `us-east-1`):
1. **IoT Core → Message routing → Rules →** `truck_location_rule` → Delete
2. **IoT Core → Things →** `truck01` → Delete. Then go to **Security → Certificates**, deactivate and delete its certificate, and delete `truck01-policy` under **Policies**.
3. **Amazon Location → Trackers →** `DeliveryTracker` → Delete. Also delete the `pdc-map-key` API key if you made one.
4. **IAM → Users →** `pdc-demo-user` → Delete. **IAM → Roles →** `iot-location-role` → Delete.
5. Delete the `certs` folder and the access-key `.csv` from your laptop.

---

## Useful links

- Amazon Location developer guide: https://docs.aws.amazon.com/location/latest/developerguide/what-is.html
- IoT rule action for Amazon Location: https://docs.aws.amazon.com/iot/latest/developerguide/location-rule-action.html
- AWS IoT Core developer guide: https://docs.aws.amazon.com/iot/latest/developerguide/what-is-aws-iot.html
- Amazon Location pricing: https://aws.amazon.com/location/pricing/
- AWS IoT Core pricing: https://aws.amazon.com/iot-core/pricing/
- AWS Free Tier: https://aws.amazon.com/free/
