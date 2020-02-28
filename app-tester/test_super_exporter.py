#consumer test
import pika, json, uuid, time, random

credentials = pika.PlainCredentials("richardm", "bigdatastack")
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost',credentials=credentials))
print("Connection to broker established ...")
channel = connection.channel()

def main():
    global channel 
    while True:
        message = {}
        metrics = {"memory": random.randint(20000,40000)}
        labels = {"application":"use_case"}
        message["metrics"] = metrics
        message["labels"] = labels
        channel.basic_publish("","export_metrics",json.dumps(message))
        print(message)
        time.sleep(10)

if __name__ == "__main__":
    main()