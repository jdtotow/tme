# Create a local image of rabbitmq with the baked in configuration
# for the exchange, queues and bindings
FROM rabbitmq:3-management
COPY rabbitmq.config /etc/rabbitmq/
COPY definitions.json /etc/rabbitmq/