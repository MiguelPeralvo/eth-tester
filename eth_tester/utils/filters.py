from queue import (
    Queue,
    Empty,
)

from eth_utils import (
    to_tuple,
    is_bytes,
    is_address,
    is_same_address,
    is_integer,
)


class Filter(object):
    values = None
    queue = None

    def __init__(self, filter_fn=None):
        self.values = []
        self.queue = Queue()
        self.filter_fn = filter_fn

    @to_tuple
    def get_changes(self):
        while True:
            try:
                yield self.queue.get_nowait()
            except Empty:
                break

    def get_all(self):
        return tuple(self.values)

    def add(self, *values):
        for item in values:
            if self.filter_fn is not None and not self.filter_fn(item):
                continue
            self.values.append(item)
            self.queue.put_nowait(item)


def is_tuple(value):
    return isinstance(value, tuple)


def is_topic_string(value):
    return is_bytes(value) and len(value) == 32


def is_topic(value):
    return value is None or is_topic_string(value)


def is_flat_topic_array(value):
    return is_tuple(value) and all(is_topic(item) for item in value)


def is_nested_topic_array(value):
    return bool(value) and is_tuple(value) and all((is_topic_array(item) for item in value))


def is_topic_array(value):
    return is_flat_topic_array(value) or is_nested_topic_array(value)


def check_single_topic_match(log_topic, filter_topic):
    if filter_topic is None:
        return True
    return filter_topic == log_topic


def check_if_from_block_match(block_number, _type, from_block):
    if from_block is None or from_block == "latest":
        return _type == "mined"
    elif from_block in {"earliest", "pending"}:
        return _type == "pending"
    elif is_integer(from_block):
        return is_integer(block_number) and block_number >= from_block
    else:
        raise ValueError("Unrecognized from_block format: {0}".format(from_block))


def check_if_to_block_match(block_number, _type, to_block):
    if to_block is None or to_block == "latest":
        return _type == "mined"
    elif to_block in {"earliest", "pending"}:
        return _type == "pending"
    elif is_integer(to_block):
        return is_integer(block_number) and block_number <= to_block
    else:
        raise ValueError("Unrecognized to_block format: {0}".format(to_block))


def check_if_log_matches_flat_topics(log_topics, filter_topics):
    if not filter_topics:
        return True
    elif len(log_topics) != len(filter_topics):
        return False
    else:
        return all(
            check_single_topic_match(left, right)
            for left, right
            in zip(log_topics, filter_topics)
        )


def check_if_topics_match(log_topics, filter_topics):
    if filter_topics is None:
        return True
    elif is_flat_topic_array(filter_topics):
        return check_if_log_matches_flat_topics(log_topics, filter_topics)
    elif is_nested_topic_array(filter_topics):
        return any(
            check_if_log_matches_flat_topics(log_topics, sub_filter_topics)
            for sub_filter_topics
            in filter_topics
        )
    else:
        raise ValueError("Unrecognized topics format: {0}".format(filter_topics))


def check_if_address_match(address, addresses):
    if addresses is None:
        return True
    if is_tuple(addresses):
        return any(
            is_same_address(address, item)
            for item
            in addresses
        )
    elif is_address(addresses):
        return is_same_address(addresses, address)
    else:
        raise ValueError("Unrecognized address format: {0}".format(addresses))


def check_if_log_matches(log_entry,
                         from_block,
                         to_block,
                         addresses,
                         topics):
    if not check_if_from_block_match(log_entry['block_number'], log_entry['type'], from_block):
        return False
    elif not check_if_to_block_match(log_entry['block_number'], log_entry['type'], to_block):
        return False
    elif not check_if_address_match(log_entry['address'], addresses):
        return False
    elif not check_if_topics_match(log_entry['topics'], topics):
        return False
    else:
        return True
