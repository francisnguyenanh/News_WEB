from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import feedparser
import requests
from bs4 import BeautifulSoup
import os
import json
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///news.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Database models
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(500), nullable=False)
    image_url = db.Column(db.String(500))
    topic = db.Column(db.String(50), nullable=False)


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    keyword = db.Column(db.String(100), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)


# Default RSS feeds
RSS_FEEDS = {
    'Technology': 'http://feeds.bbci.co.uk/news/technology/rss.xml',
    'Sports': 'http://feeds.bbci.co.uk/news/sport/rss.xml',
    'Politics': 'http://feeds.bbci.co.uk/news/politics/rss.xml'
}

# Ensure theme.txt exists
if not os.path.exists('theme.txt'):
    with open('theme.txt', 'w') as f:
        f.write('#ffffff')  # Default background: white


def get_contrast_color(bg_color):
    # Default color if input is invalid
    default_color = '#ffffff'

    # Validate hex color format (e.g., #FFFFFF or FFFFFF)
    if not bg_color:
        bg_color = default_color

    # Remove # if present
    bg_color = bg_color.lstrip('#')

    # Check if it's a valid 6-digit hex color
    if not re.match(r'^[0-9a-fA-F]{6}$', bg_color):
        bg_color = default_color.lstrip('#')  # Use default if invalid

    try:
        # Convert hex to RGB
        r, g, b = int(bg_color[:2], 16), int(bg_color[2:4], 16), int(bg_color[4:], 16)
        # Calculate luminance
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        # Return black for light backgrounds, white for dark
        return '#000000' if luminance > 0.5 else '#ffffff'
    except ValueError:
        # Fallback to default color if conversion fails
        return get_contrast_color(default_color)


def get_news(topic, keyword):
    feed_url = RSS_FEEDS.get(topic)
    articles = []
    if feed_url:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:10]:  # Limit to 10 articles
            image_url = None
            try:
                # Try to extract image from content or summary
                soup = BeautifulSoup(entry.get('summary', ''), 'html.parser')
                img = soup.find('img')
                if img and 'src' in img.attrs:
                    image_url = img['src']
            except:
                pass
            articles.append({
                'title': entry.get('title', 'No Title'),
                'description': entry.get('summary', 'No Description'),
                'url': entry.get('link', '#'),
                'image_url': image_url,
                'topic': topic
            })
    return articles


@app.route('/')
def index():
    try:
        with open('theme.txt', 'r') as f:
            bg_color = f.read().strip()
    except:
        bg_color = '#ffffff'  # Fallback if file read fails
    text_color = get_contrast_color(bg_color)

    topics = Topic.query.all()
    all_articles = []
    for topic in topics:
        if topic.is_visible:
            articles = get_news(topic.name, topic.keyword)
            all_articles.extend(articles)

    return render_template('index.html', articles=all_articles, topics=topics,
                           bg_color=bg_color, text_color=text_color)


@app.route('/save_article', methods=['POST'])
def save_article():
    title = request.form['title']
    description = request.form['description']
    url = request.form['url']
    image_url = request.form.get('image_url')
    topic = request.form['topic']

    article = Article(title=title, description=description, url=url,
                      image_url=image_url, topic=topic)
    db.session.add(article)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/saved')
def saved():
    try:
        with open('theme.txt', 'r') as f:
            bg_color = f.read().strip()
    except:
        bg_color = '#ffffff'  # Fallback if file read fails
    text_color = get_contrast_color(bg_color)

    articles = Article.query.all()
    topics = Topic.query.all()
    return render_template('saved.html', articles=articles, topics=topics,
                           bg_color=bg_color, text_color=text_color)


@app.route('/delete_article/<int:id>')
def delete_article(id):
    article = Article.query.get_or_404(id)
    db.session.delete(article)
    db.session.commit()
    return redirect(url_for('saved'))


@app.route('/change_theme', methods=['POST'])
def change_theme():
    bg_color = request.form['bg_color']
    # Validate color before saving
    bg_color = bg_color.lstrip('#')
    if re.match(r'^[0-9a-fA-F]{6}$', bg_color):
        with open('theme.txt', 'w') as f:
            f.write('#' + bg_color)
    return redirect(url_for('index'))


@app.route('/toggle_topic/<int:id>', methods=['POST'])
def toggle_topic(id):
    topic = Topic.query.get_or_404(id)
    topic.is_visible = not topic.is_visible
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/add_topic', methods=['POST'])
def add_topic():
    name = request.form['name']
    keyword = request.form['keyword']
    if name and keyword and name not in RSS_FEEDS:
        topic = Topic(name=name, keyword=keyword)
        db.session.add(topic)
        db.session.commit()
        RSS_FEEDS[name] = f'http://feeds.bbci.co.uk/news/{keyword.lower()}/rss.xml'
    return redirect(url_for('index'))


@app.route('/delete_topic/<int:id>')
def delete_topic(id):
    topic = Topic.query.get_or_404(id)
    if topic.name in RSS_FEEDS:
        del RSS_FEEDS[topic.name]
    db.session.delete(topic)
    db.session.commit()
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Initialize default topics if not exist
        for name, url in RSS_FEEDS.items():
            if not Topic.query.filter_by(name=name).first():
                topic = Topic(name=name, keyword=name.lower())
                db.session.add(topic)
        db.session.commit()
    app.run(debug=True)