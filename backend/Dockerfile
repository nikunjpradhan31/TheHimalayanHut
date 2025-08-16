FROM continuumio/miniconda3:latest

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

RUN conda env create -f environment_linux.yml && conda clean -a -y

ENV PATH=/opt/conda/envs/HimalEnv/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 7001

CMD ["conda", "run", "--no-capture-output", "-n", "HimalEnv", "python", "main.py"]
