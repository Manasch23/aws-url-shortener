# AWS URL Shortener

Paste a long URL to create a shareable link. Each time someone opens the link, the app redirects them to the original page and adds one to the visit count.

[Try the live app](https://manasch23.github.io/aws-url-shortener/)

## What we used

- **HTML, CSS, and JavaScript** for the interface, hosted on **GitHub Pages**.
- **Python on AWS Lambda** to create links, handle redirects, and return visit counts.
- **Amazon DynamoDB** to store short codes, original URLs, and visit counts.
- **AWS CloudFormation and IAM** to deploy the AWS resources and give Lambda access to the table.
