from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import warnings
import threading

from ClientManager import ClientManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    A context manager that sets up various configurations for the FastAPI app and handles startup and shutdown routines.
    Takes in a FastAPI instance as a parameter.
    Yields control back to the caller after startup configurations are completed.
    """
    app.clientMan = ClientManager()
    #app.clientMan.updateServers = True

    # Start the reconnect loop in a separate thread
    reconnect_thread = threading.Thread(target=app.clientMan.reconnect_loop)
    reconnect_thread.start()

    yield

    # Stop the client manager and the reconnect loop
    app.clientMan.stop()
    reconnect_thread.join()
