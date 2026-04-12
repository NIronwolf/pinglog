from pinglog.db.queries import insert_log


def parse_reply(reply):
    print(f"Parsing reply: #{reply}")
    insert_log(reply.chat_id, reply.text, 10)
