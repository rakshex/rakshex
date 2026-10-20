"""Synthetic migration regression fixture, never a real provider integration."""
import requests


def create_order(customer):
    return requests.post('https://api.example.com/v1/orders', json={'customer_ref': customer})
