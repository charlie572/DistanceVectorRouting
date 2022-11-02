from random import choice

import networkx as nx
from matplotlib import pyplot as plt


def process_route_update(network, node, message):
    routing_table = network.nodes[node]["routing_table"]

    routes = []
    for destination, distance in message["routes"]:
        if destination == node:
            continue
        if message["source"] not in routing_table:
            continue

        new_distance = distance + 1
        if (
            destination not in routing_table
            or new_distance <= routing_table[destination][1]
        ):
            routing_table[destination] = message["source"], new_distance
            routes.append((destination, new_distance))

    if len(routes) > 0:
        message = {"type": "route_update", "routes": routes}
        send_to_neighbours(network, node, message)


def process_route_request(network, node, message):
    routing_table = network.nodes[node]["routing_table"]
    routes = [(dest, dist) for dest, (_, dist) in routing_table.items()]
    send(network, node, message["source"], {"type": "route_update", "routes": routes})


def process_route_lost(network, node, message):
    routing_table = network.nodes[node]["routing_table"]

    for destination, (next_hop, _) in list(routing_table.items()):
        if next_hop == message["source"] and destination == message["destination"]:
            routing_table.pop(destination)
            send_to_neighbours(
                network,
                node,
                {"type": "route_lost", "destination": destination},
                exclude={message["source"]},
            )
        else:
            send_to_neighbours(
                network,
                node,
                {"type": "route_update", "routes": [routing_table[destination]]},
            )


def process_message(network, node, message):
    if message["type"] == "route_update":
        process_route_update(network, node, message)
    elif message["type"] == "route_request":
        process_route_request(network, node, message)
    elif message["type"] == "route_lost":
        process_route_lost(network, node, message)


def send(network, source, destination, message):
    assert network.has_edge(source, destination)
    message["source"] = source
    network.nodes[destination]["receive_buffer"].append(message)


def send_to_neighbours(network, source, message, exclude=None):
    exclude = exclude or set()

    message["source"] = source
    for destination in network.neighbors(source):
        if destination not in exclude:
            network.nodes[destination]["receive_buffer"].append(message)


def simulate(network):
    loop = True
    while loop:
        loop = False
        for node, node_data in network.nodes(data=True):
            routing_table = node_data["routing_table"]

            neighbours_in_routing_table = set(
                n for n, (_, distance) in routing_table.items() if distance == 1
            )
            actual_neighbours = set(network.neighbors(node))

            # send route requests to newly connected nodes
            for neighbour in actual_neighbours.difference(neighbours_in_routing_table):
                loop = True
                routing_table[neighbour] = neighbour, 1
                send(network, node, neighbour, {"type": "route_request"})

            # tell neighbours about nodes that have been disconnected
            for neighbour in neighbours_in_routing_table.difference(actual_neighbours):
                loop = True

                for destination, (next_hop, _) in list(routing_table.items()):
                    if next_hop == neighbour:
                        routing_table.pop(destination)
                        send_to_neighbours(
                            network,
                            node,
                            {"type": "route_lost", "destination": destination},
                        )

            # process messages received
            for message in node_data["receive_buffer"]:
                loop = True
                process_message(network, node, message)

            node_data["receive_buffer"].clear()


def send_initial_messages(network):
    for source, source_data in network.nodes(data=True):
        for destination in network.neighbors(source):
            source_data["routing_table"][destination] = destination, 1

        message = {
            "type": "route_update",
            "source": source,
            "routes": [
                (dest, dist) for dest, (_, dist) in source_data["routing_table"].items()
            ],
        }
        for destination in network.neighbors(source):
            network.nodes[destination]["receive_buffer"].append(message)


def verify_routing_tables(network):
    for node, node_data in network.nodes(data=True):
        routing_table = node_data["routing_table"]
        for destination, (next_hop, distance) in routing_table.items():
            try:
                shortest_paths = list(
                    nx.all_shortest_paths(network, source=node, target=destination)
                )
            except nx.exception.NetworkXNoPath:
                return False

            if len(shortest_paths[0]) == 1:
                return False
            if all(p[1] != next_hop for p in shortest_paths):
                return False
            if len(shortest_paths[0]) - 1 != distance:
                return False

    return True


def main():
    # generate random connected graph
    network = nx.gnp_random_graph(10, 0.3)
    network = nx.subgraph(
        network, max(nx.connected_components(network), key=len)
    ).copy()

    for _, data in network.nodes(data=True):
        data.update({"receive_buffer": [], "routing_table": {}})

    for _ in range(10):
        simulate(network)

        for node, data in network.nodes(data=True):
            print(node, data["routing_table"])
        print(verify_routing_tables(network))
        print()

        nx.draw(network, with_labels=True)
        plt.show()

        u, v = choice(list(network.edges))
        network.remove_edge(u, v)


if __name__ == "__main__":
    main()
