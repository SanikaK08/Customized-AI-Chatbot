// frontend/app.js
import express from 'express';
import bodyParser from 'body-parser';
import axios from 'axios';
import multer from 'multer';
// import cors from 'cors';
import 'dotenv/config';
import path from 'path';
import { fileURLToPath } from 'url';
import FormData from 'form-data';
import stream from 'stream';



// app.use(cors());
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);



const app = express();

// Serve static HTML files from "public" folder
app.use(express.static(path.join(__dirname, 'public')));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.post('/converse', async (req, res) => {
  const userMessage = req.body.message;

  try {
    const response = await axios.post('http://127.0.0.1:5000/ask', {
      question: userMessage,
    });

    res.send({
      role: 'assistant',
      content: response.data.reply,
    });

  } catch (error) {
    console.error("Gemini backend error:", error.message);
    res.status(500).send("Something went wrong.");
  }
});


app.get('/admin', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'admin.html'));
});


// Fetch file list from Flask backend
app.get('/admin/files', async (req, res) => {
  try {
    const response = await axios.get('http://127.0.0.1:5000/admin/files');
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching file list:', error.message);
    res.status(500).send('Error fetching file list');
  }
});


// Upload file to Flask backend
const upload = multer();
// ---- FIXED Upload Route ----
app.post('/admin/upload', upload.single('file'), async (req, res) => {
  try {
    const formData = new FormData();
    formData.append('file', req.file.buffer, req.file.originalname);

    const response = await axios.post('http://127.0.0.1:5000/admin/upload', formData, {
      headers: formData.getHeaders(),
    });

    res.send(response.data);
  } catch (error) {
    console.error('Upload error:', error.message);
    res.status(500).send('File upload failed');
  }
});


// -------------------------------



app.listen(process.env.PORT || 3000, () => {
  console.log(`Frontend running on port ${process.env.PORT || 3000}`);
});
