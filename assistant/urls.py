from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/chat/", views.chat_api, name="chat_api"),
    path("api/stats/", views.stats_api, name="stats_api"),
    path("api/weather/", views.weather_api, name="weather_api"),
    path("api/clock/", views.clock_api, name="clock_api"),
    path("api/history/", views.history_api, name="history_api"),
]
