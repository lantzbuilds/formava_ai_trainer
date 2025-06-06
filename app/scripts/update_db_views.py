#!/usr/bin/env python3
import logging

from app.config.database import Database


def main():
    logging.basicConfig(level=logging.INFO)
    db = Database()
    db.recreate_all_design_documents()
    logging.info("All design documents updated successfully.")


if __name__ == "__main__":
    main()
