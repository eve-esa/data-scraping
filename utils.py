import logging
import yaml


def setup_logging(log_file_path="./results.log"):
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        filemode="w",  # 'w' mode will overwrite the log file each time, 'a' to append
        format="%(name)s - %(levelname)s - %(message)s",
    )


# Load the YAML file
def read_yaml_file(file_path: str):
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    return data


# for publisher, details in data["publishers"].items():
#     print(f"Publisher: {publisher}")
#     for journal in details["journals"]:
#         print(f"  Journal Name: {journal['name']}")
#         print(f"  URL: {journal['url']}")
#         print(f"  ISSN: {journal['ISSN']}")
#         print(
#             f"  Volume Range: {journal['volume_range']['start']} to {journal['volume_range']['end']}"
#         )
#         print(
#             f"  Issue Range: {journal['issue_range']['start']} to {journal['issue_range']['end']}"
#         )
