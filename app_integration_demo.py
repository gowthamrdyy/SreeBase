import time
import random
from reddybase.client.driver import Client, ReddyBaseError

def main():
    print("Initializing Server Monitoring Demo with ReddyBase...")
    
    # 1. Connect to SreeBase
    try:
        client = Client(host="127.0.0.1", port=6969)
        # Assuming admin/secret was created in previous steps; comment out if auth is disabled.
        try:
            client.login("admin", "secret")
        except ReddyBaseError as e:
            print(f"Skipping login or login failed: {e}")
            
        print("Connected to SreeBase server successfully.")
    except Exception as e:
        print(f"Failed to connect to SreeBase: {e}")
        print("Please ensure the SreeBase server is running on port 6969.")
        return

    logs = client.collection("server_logs")
    
    # Optional: create index on server_id and status for fast analytical querying
    try:
        client.raw_query('create index on server_logs field status\n')
        print("Ensured index on 'status' field.")
    except ReddyBaseError:
        pass # Ignore if already exists or permission denied

    # 2. Simulate High-Scale Ingestion
    print("\n--- Starting Log Ingestion ---")
    servers = ["srv-alpha", "srv-beta", "srv-gamma"]
    statuses = ["ok", "warning", "critical"]
    
    for i in range(10):
        doc = {
            "server_id": random.choice(servers),
            "cpu": round(random.uniform(10.0, 99.9), 2),
            "memory": round(random.uniform(20.0, 95.0), 2),
            "status": random.choices(statuses, weights=[0.8, 0.15, 0.05])[0],
            "timestamp": int(time.time())
        }
        logs.insert(doc)
        print(f"Inserted log: {doc['server_id']} - CPU: {doc['cpu']}% - Status: {doc['status']}")
        time.sleep(0.1)

    # 3. Retrieve Data (ORM wrapper)
    print("\n--- Fetching Critical Logs ---")
    critical_logs = logs.get(where={"status": '= "critical"'})
    if not critical_logs:
        print("No critical logs found. (System is healthy!)")
    else:
        for log in critical_logs:
            print(f"CRITICAL ALERT: {log['server_id']} CPU at {log['cpu']}%")

    # 4. Aggregation Analytics
    print("\n--- Real-time Analytics (Average CPU per Server) ---")
    try:
        analytics = logs.aggregate(
            group_by="server_id", 
            calculate=["count()", "avg(cpu)", "avg(memory)"]
        )
        for stat in analytics:
            print(f"Server {stat['server_id']}: Count={stat['count()']}, Avg CPU={round(stat['avg(cpu)'], 2)}%, Avg Mem={round(stat['avg(memory)'], 2)}%")
    except ReddyBaseError as e:
        print(f"Aggregation error: {e}")
        
    client.close()

if __name__ == "__main__":
    main()
