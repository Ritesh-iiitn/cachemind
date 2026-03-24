# 📄 DocChat GenAI

🚀 DocChat GenAI is a Retrieval-Augmented Generation (RAG) based intelligent document assistant that enables users to upload PDFs, research papers, or notes and interact with them using natural language.

The system leverages modern Generative AI techniques such as semantic embeddings, vector search, and Large Language Models (LLMs) to provide contextual answers, summaries, and knowledge extraction.

---

## ✨ Features

- 📂 Upload PDF / Research Papers / Notes
- 💬 Ask questions from document content
- 🧠 Context-aware answers using RAG
- 📝 Automatic document summarization
- ❓ Quiz generation from document knowledge
- ⚡ Semantic search powered by embeddings
- 🧩 Modular GenAI architecture

---

## 🏗️ System Architecture

User Upload → Text Extraction → Chunking → Embeddings → Vector DB (FAISS)  
→ RAG Pipeline → LLM → Smart Response

---

## 🧠 Tech Stack

### Backend
- Django
- Django REST Framework

### GenAI
- LangChain
- Retrieval-Augmented Generation (RAG)

### LLM
- Groq API / OpenAI / Gemini (configurable)

### Embeddings
- OpenAI Embeddings

### Vector Database
- FAISS

### Document Parsing
- PyMuPDF / PyPDF

---

## 📁 Project Structure

ai_doc_assistant/  
│  
├── apps/  
├── ai_engine/  
├── config/  
├── vector_store/  
├── templates/  
├── static/  
├── media/  
├── manage.py  
└── requirements.txt  

---

## ⚙️ Installation

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Ritesh-iiitn/docchat-genai.git
cd docchat-genai
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # mac/linux
venv\Scripts\activate      # windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Setup Environment Variables

Create `.env` file:

```
GROQ_API_KEY=your_api_key_here
```

### 5️⃣ Run Migrations

```bash
python manage.py migrate
```

### 6️⃣ Run Server

```bash
python manage.py runserver
```

---

## 🧠 How It Works (RAG Flow)

1. User uploads document  
2. Text is extracted and chunked  
3. Embeddings are generated  
4. Stored in FAISS vector database  
5. User query retrieves relevant chunks  
6. LLM generates contextual answer  

---

## 🚀 Future Improvements

- Multi-document chat
- Conversation memory
- Knowledge graph generation
- PDF highlighting with answer mapping
- UI dashboard analytics
- Model fine-tuning
- Streaming responses

---

## 📌 Use Cases

- Research paper understanding
- Student study assistant
- Knowledge management system
- AI powered documentation tool
- Enterprise knowledge retrieval

---

## 🧑‍💻 Author

Ritesh Singh  
Computer Science Student | Backend + AI Developer  

---

## ⭐ If you like this project

Give it a ⭐ on GitHub 🙂
