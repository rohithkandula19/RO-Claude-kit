"""Deliberately buggy code for the code-reviewer example to chew on.

Five things wrong here. The reviewers should catch most of them.
"""
import os
import subprocess


def calculate_discount(price, discount_percent):
    # Bug: no validation of discount_percent range
    return price - (price * discount_percent / 100)


def get_user_data(user_id):
    # Bug: SQL injection — user_id interpolated into query
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute_query(query)


def execute_query(q):
    pass  # placeholder


def run_command(cmd):
    # Bug: shell=True with user input is a command-injection foot-gun
    return subprocess.check_output(cmd, shell=True).decode()


def cache_user_files(user_id):
    # Bug: writing to /tmp without sanitizing user_id allows path traversal
    path = f"/tmp/cache_{user_id}.txt"
    with open(path, "w") as f:
        f.write("cached")
    return path


API_KEY = "sk-prod-9f8a7b6c5d4e3f2a1b0c"  # Bug: hardcoded secret in source


def divide(a, b):
    # Bug: no zero-check
    return a / b
