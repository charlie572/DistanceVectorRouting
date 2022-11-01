import networkx as nx
from matplotlib import pyplot as plt


def verify_routing_tables(network):
    for node, node_data in network.nodes(data=True):
        routing_table = node_data["routing_table"]
        for destination, (next_hop, distance) in routing_table.items():
            shortest_paths = list(
                nx.all_shortest_paths(network, source=node, target=destination)
            )
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
    network: nx.Graph = nx.subgraph(
        network, max(nx.connected_components(network), key=len)
    )

    for _, data in network.nodes(data=True):
        data.update({"receive_buffer": [], "routing_table": {}})

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

    for node, node_data in network.nodes(data=True):
        print(node, node_data["routing_table"])
    print()

    loop = True
    while loop:
        loop = False
        for node, node_data in network.nodes(data=True):
            routing_table = node_data["routing_table"]

            for message in node_data["receive_buffer"]:
                if message["type"] != "route_update":
                    continue

                loop = True

                routes = []
                for destination, distance in message["routes"]:
                    if destination == node:
                        continue

                    new_distance = distance + routing_table[message["source"]][1]
                    if (
                        destination not in routing_table
                        or new_distance < routing_table[destination][1]
                    ):
                        routing_table[destination] = message["source"], new_distance
                        routes.append((destination, new_distance))

                if len(routes) > 0:
                    message = {"type": "route_update", "source": node, "routes": routes}
                    for neighbour in network.neighbors(node):
                        network.nodes[neighbour]["receive_buffer"].append(message)

            node_data["receive_buffer"].clear()

        for node, node_data in network.nodes(data=True):
            print(node, node_data["routing_table"])
        print()

    print(verify_routing_tables(network))

    nx.draw(network, with_labels=True)
    plt.show()


if __name__ == "__main__":
    main()
