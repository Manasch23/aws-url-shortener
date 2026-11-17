# Cloud-Based URL Shortener with Visit Analytics

A small student project that creates shareable links and tracks how many times each link is opened. The demo runs on AWS Lambda and Amazon DynamoDB.

- [Project website](https://manasch23.github.io/aws-url-shortener/)
- [Direct AWS app](https://7xzhhpubyas6dpbrblq6np35ay0msewx.lambda-url.ap-southeast-2.on.aws/)

## Requirements

| Where | What you need |
| --- | --- |
| Local preview | Python 3.12 and a browser. Python's standard library is enough. |
| AWS deployment | AWS account or lab account and AWS CLI v2. Your AWS identity needs permission to deploy the CloudFormation stack and create its Lambda, DynamoDB, IAM, and CloudWatch Logs resources. |
| AWS region | A region supporting Lambda Function URLs. The deployment example uses `ap-southeast-2` (Sydney). |

The app uses the AWS SDK that comes with the Python Lambda runtime. Python builds an inline CloudFormation template, so AWS CLI can deploy it directly. AWS usage charges depend on the account and traffic.

## Project structure

```text
aws-url-shortener/
├── README.md       Setup, deployment, demo, and viva notes
├── template.json   CloudFormation template for the AWS resources
├── build.py        Embeds the source and HTML in the deployable template
├── preview.py      Local HTTP server backed by SQLite
├── .gitignore     Ignores local database, cache, and build files
└── src/
    ├── app.py      HTTP routes and DynamoDB operations
    └── index.html Browser interface with CSS and JavaScript
```

## How it works

```text
Browser → Lambda Function URL → Python Lambda → DynamoDB
                                   ↓
                  Web page, visit count, or HTTP 302 redirect
```

DynamoDB stores one item per short link. Its fields are `code` (string partition key), `destination` (URL), and `visits` (number). The app generates an eight-character code and uses a conditional write to avoid overwriting a link if the code collides.

| Method and path | Result |
| --- | --- |
| `GET /` | Shows the shorten form. `/?code=...` also reopens a saved stats view. |
| `POST /api/links` | Accepts JSON such as `{"url":"https://example.com/events/registration"}` and returns a short path. |
| `GET /r/{code}` | Atomically increments the count and returns an HTTP 302 redirect. |
| `GET /api/stats/{code}` | Reads the current count. Unknown codes return HTTP 404. |

An open counts when the app handles a redirect request. Repeat opens and automated link previews can both count. Refreshing the stats view only reads the counter. The AWS-generated hostname is long, so the demo illustrates how a short code replaces a long destination path and query string.

## Run locally on Windows

Open PowerShell in the project folder and run:

```powershell
python preview.py
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765) in your browser. The server creates a SQLite database file named `.preview.sqlite3` for local links. Press **Ctrl+C** in PowerShell to stop it. Build a new link after deploying to AWS because each environment has its own database.

## Deploy to AWS

For a standard AWS Console account that supports CLI login, connect from your own PowerShell. Complete the sign-in in your browser. If your lab gives you a configured CLI profile, use that profile name and your lab's required region in the commands.

```powershell
aws login --profile llt1 --region ap-southeast-2
aws sts get-caller-identity --profile llt1 --region ap-southeast-2
```

From the project folder, build and deploy the template. The Function URL is public so your teacher can open it. The IAM role grants the function access to this project's DynamoDB table and its log group.

```powershell
python build.py
aws cloudformation deploy --template-file .build/stack.json --stack-name aws-url-shortener --capabilities CAPABILITY_IAM --region ap-southeast-2 --profile llt1 --no-fail-on-empty-changeset
```

When deployment finishes, find **AppUrl** in the stack outputs and open it in your browser. Copy that URL into your class sheet's **Project Link** column. Find the CloudFormation outputs again with:

```powershell
aws cloudformation describe-stacks --stack-name aws-url-shortener --region ap-southeast-2 --profile llt1 --query "Stacks[0].Outputs"
```

## Optional GitHub Pages address

GitHub Pages can serve the same interface at `https://USERNAME.github.io/aws-url-shortener/`. The page still calls AWS Lambda to create links and read stats. Generated redirect links use the AWS Function URL.

1. Redeploy the AWS stack with the extra option `--parameter-overrides PagesOrigin=https://USERNAME.github.io`, using the GitHub repository owner's username. This lets the Pages site call Lambda from the browser.
2. Run `python build.py --pages YOUR_APP_URL`, replacing `YOUR_APP_URL` with the stack's **AppUrl**. This generates the `docs/` directory.
3. Push the source and generated `docs/` to GitHub. In the repository, open **Settings → Pages**, choose **Deploy from a branch**, and select **main** and **/docs**.

## Clean up

Public usage can create billable requests. Delete the stack when the class has finished with it. This removes the app and its saved links.

```powershell
aws cloudformation delete-stack --stack-name aws-url-shortener --region ap-southeast-2 --profile llt1
```

## LLT1 demonstration

1. Introduce AWS as the cloud platform. Explain that Lambda is serverless compute and DynamoDB is a managed NoSQL database.
2. Paste `https://example.com/?event=college-fest&source=poster` into the form and click **Shorten URL**. Show the new short link and **0** visits.
3. Click **Open link** twice. Show that both opens land on the destination page.
4. Click **Refresh count** and show **2** visits. In the DynamoDB console, open **Explore table items** for the table named in the **TableName** output and show the same value.
5. Describe a college fest using separate links for an Instagram bio and a poster QR code. Both lead to the same registration form, while the separate counters show which source drove more visits.

### Viva questions

- **Why Lambda?** It runs the Python code on each request. AWS manages the runtime infrastructure.
- **Why use the short code as the DynamoDB partition key?** Lambda can find the matching destination directly from the code in the request.
- **What does HTTP 302 do?** It tells the browser to open the destination listed in the response's `Location` header.
- **What happens if two people open the link together?** DynamoDB applies each increment atomically, so concurrent requests can each add one to the counter.
- **How does an unknown link behave?** Lambda returns HTTP 404, and DynamoDB does not create a record for the unknown code.
