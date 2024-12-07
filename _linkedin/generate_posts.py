import os
import json
import re
from linkedin_api import Linkedin
from datetime import datetime

# LinkedIn API kimlik doğrulama
api = Linkedin(os.getenv('LINKEDIN_EMAIL'), os.getenv('LINKEDIN_PASSWORD'))
posts = api.get_profile_posts('aliylmz', post_count=20)
user_posts = [post for post in posts if post['actor']['urn'] == 'urn:li:member:432295887']

def extract_activity_number(dash_entity_urn):
    match = re.search(r'urn:li:activity:(\d+)', dash_entity_urn)
    return match.group(1) if match else None

def convert_activity_number_to_time(activity_number):
    if activity_number is None:
        return None
    binary_representation = bin(int(activity_number))[2:]
    timestamp_binary = binary_representation[:41]
    timestamp_ms = int(timestamp_binary, 2)
    timestamp_seconds = timestamp_ms / 1000
    return datetime.utcfromtimestamp(timestamp_seconds)

posts_summary = []
for post_index, post in enumerate(user_posts):
    post_summary = {
        'post': post_index,
        'activity_id': None,
        'time': None,
        'text': None,
        'images': []
    }
    dash_entity_urn = post.get('dashEntityUrn', '')
    activity_number = extract_activity_number(dash_entity_urn)
    post_summary['activity_id'] = activity_number

    post_time = convert_activity_number_to_time(activity_number)
    post_summary['time'] = post_time.strftime('%Y-%m-%d %H:%M:%S Z') if post_time else None

    post_text = post.get('commentary', {}).get('text', {}).get('text', None)
    post_summary['text'] = post_text

    images = post.get('content', {}).get('com.linkedin.voyager.feed.render.ImageComponent', {}).get('images', [])
    for image in images:
        root_url = image.get('attributes', [{}])[0].get('vectorImage', {}).get('rootUrl', '')
        artifact = image.get('attributes', [{}])[0].get('vectorImage', {}).get('artifacts', [{}])[0]
        file_path = artifact.get('fileIdentifyingUrlPathSegment', '')
        if root_url and file_path:
            full_url = root_url + file_path
            post_summary['images'].append({'url': full_url})

    posts_summary.append(post_summary)

with open('posts_summary.json', 'w', encoding='utf-8') as f:
    json.dump(posts_summary, f, indent=4, ensure_ascii=False)

# Yeni gönderileri markdown dosyasına yazma
with open('posts_summary.json', 'r', encoding='utf-8') as f:
    posts = json.load(f)

existing_posts = [f for f in os.listdir('_posts') if f.endswith('.md')]
existing_activity_ids = []

for filename in existing_posts:
    with open(os.path.join('_posts', filename), 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('activity_id:'):
                existing_activity_ids.append(line.split(':')[1].strip())

for post in posts:
    if post['activity_id'] not in existing_activity_ids:
        filename = f"_posts/{post['time']}.md"
        title = post['text'][:10] + '...'
        content = f"""---
title: {title}
date: {post['time']}
categories:
- linkedin
tags:
- linkedin
layout: post
description: {title}
featured: true
activity_id: {post['activity_id']}
---

{post['text']}
{post['images']}
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
