# Instant CTF
[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/ahmedQuadimi/Instant_CTF)

Instant CTF is a comprehensive, open-source platform for hosting and participating in Capture The Flag (CTF) competitions. Built with Django, it provides a full suite of features for event organizers and competitors, inspired by the best aspects of platforms like CTFTime and CTFd.

## Features

- **Event Management**: Create and manage public or private CTF events, complete with start/end times, team size limits, and custom scoring rules.
- **Organization System**: Group events under organizations, allowing for streamlined management and permission handling for event staff.
- **Dynamic & Static Scoring**: Supports multiple scoring strategies, including static points per challenge, and dynamic scoring that adjusts challenge value based on the number of solves.
- **Team Management**: Players can create teams, manage memberships, and handle join requests. Team captains can register their entire team for an event.
- **Challenge Hosting**: Organizers can create challenges across various categories, set points, provide descriptions with Markdown support, attach files, and schedule release times.
- **Live Scoreboard**: A real-time, auto-refreshing scoreboard tracks team rankings, scores, and solve times during active events.
- **User Authentication**: Supports local email/password registration and social authentication via Google OAuth, with user profiles to track participation.
- **Role-Based Access Control**: Granular control with distinct roles for Site Admins, Organization Owners/Admins, Event Owners/Admins, and Players.

## Technology Stack

- **Backend**: Django
- **Database**: PostgreSQL (Production) / SQLite3 (Development)
- **Authentication**: `django-allauth` for email/password and Google OAuth2
- **File Storage**: `django-supabase-storage` for integration with Supabase for file uploads.
- **Frontend**: Django Template Language (DTL), HTML, and vanilla CSS/JavaScript.

## Project Structure

The project is organized into several modular Django apps:

- **`Accounts`**: Manages user models, profiles, authentication, and site-level roles.
- **`Organizations`**: Handles the creation and management of organizations and their membership/roles.
- **`Events`**: The core application for CTF event creation, management, registration, and access control.
- **`Teams`**: Manages team creation, membership, and join requests.
- **`Challenges`**: Governs challenges, including creation, flag hashing, and file attachments.
- **`Scoring`**: Processes flag submissions, calculates points, records solves, and powers the scoreboard logic.

## Getting Started

Follow these steps to run a local instance of Instant CTF.

### Prerequisites

- Python 3.10+
- PostgreSQL or another compatible database for production (SQLite is used for default local development).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ahmedQuadimi/Instant_CTF.git
    cd Instant_CTF
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    # On Windows, use: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the project root and add the following variables. For local development, a `SECRET_KEY` and the default `DATABASE_URL` are sufficient.

    ```env
    # A strong, unique secret key for your Django application
    SECRET_KEY="your-super-secret-key"

    # Set to True for local development
    DEBUG=True

    # Allowed hosts for the server (e.g., "127.0.0.1,localhost")
    ALLOWED_HOSTS=".localhost,127.0.0.1,[::1]"

    # Database URL (defaults to a local SQLite file)
    DATABASE_URL="sqlite:///db.sqlite3"

    # Google OAuth2 Credentials (optional, for social login)
    GOOGLE_CLIENT_ID="your-google-client-id"
    GOOGLE_CLIENT_SECRET="your-google-client-secret"

    # Supabase Storage Credentials (optional, for file attachments)
    SUPABASE_URL="https://your-project.supabase.co"
    SUPABASE_KEY="your-supabase-service-key"
    SUPABASE_STORAGE_BUCKET_NAME="your-storage-bucket-name"
    ```

5.  **Apply database migrations:**
    ```bash
    python manage.py migrate
    ```

6.  **Create a superuser:**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```

The application will be available at `http://127.0.0.1:8000`.

## Usage

### For Players
- **Register**: Create an account using email or Google.
- **Team Up**: Create a new team or browse public teams to request to join.
- **Find Events**: Browse the list of public CTF events.
- **Compete**: Register for an active event, view challenges, submit flags, and track your team's progress on the live scoreboard.

### For Organizers
- **Create an Organization**: Start by creating an organization to host your events. As the creator, you become the Owner.
- **Create an Event**: From the Events page, create a new event under your organization. You can set its visibility, schedule, team size, and scoring model.
- **Manage Event**: Use the "Manage" tab in your event dashboard to add challenges, manage participants, and generate invite links for private events.
- **Add Challenges**: Define challenge categories, descriptions, points, and correct flags. You can also attach files and set scheduled release times.