from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import warnings
import threading

from Client.ClientManager import ClientManager
from Constants.Constants import Constants
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    A context manager that sets up various configurations for the FastAPI app and handles startup and shutdown routines.
    Takes in a FastAPI instance as a parameter.
    Yields control back to the caller after startup configurations are completed.
    """
    app.constants = Constants()
    app.clientMan = ClientManager(app.constants)
    #app.clientMan.updateServers = True

    reconnect_thread = threading.Thread(target=app.clientMan.reconnect_loop)
    reconnect_thread.start()

    yield

    # Stop the client manager and the reconnect loop
    app.clientMan.stop()
    reconnect_thread.join()
