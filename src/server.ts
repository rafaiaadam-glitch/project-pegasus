import express from "express";
import {
  getDailyStudy,
  postLectureProcess,
  postLectureUpload,
  postThreadUpsert,
} from "./endpoints.js";

const app = express();
app.use(express.json({ limit: "5mb" }));

app.post("/lectures/upload", (req, res) => {
  try {
    const result = postLectureUpload(req.body);
    res.status(result.status).json(result.body);
  } catch (error) {
    res.status(400).json({ error: (error as Error).message });
  }
});

app.post("/lectures/process", (req, res) => {
  try {
    const result = postLectureProcess(req.body);
    res.status(result.status).json(result.body);
  } catch (error) {
    res.status(400).json({ error: (error as Error).message });
  }
});

app.post("/threads/upsert", (req, res) => {
  try {
    const result = postThreadUpsert(req.body);
    res.status(result.status).json(result.body);
  } catch (error) {
    res.status(400).json({ error: (error as Error).message });
  }
});

app.post("/study/daily", (req, res) => {
  try {
    const result = getDailyStudy(req.body);
    res.status(result.status).json(result.body);
  } catch (error) {
    res.status(400).json({ error: (error as Error).message });
  }
});

const port = Number(process.env.PORT ?? 3000);
app.listen(port, () => {
  console.log(`Pegasus API server listening on port ${port}.`);
});
