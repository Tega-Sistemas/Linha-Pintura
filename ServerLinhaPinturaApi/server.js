import express from "express";
import fs from "fs";
import path from "path";
import axios from 'axios';
import dotenv from 'dotenv';
import cron from 'node-cron';
import archiver from 'archiver';

dotenv.config();

const app = express();
const PORT = 3500;

// Middleware para parse de JSON
app.use(express.json());

// Criar a pasta /logs se não existir
const logsDir = path.join("./logs");
if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });

// Criar a pasta /logfiles se não existir
const logFilesDir = path.join("./logfiles");
if (!fs.existsSync(logFilesDir)) fs.mkdirSync(logFilesDir, { recursive: true });

// ---------------------------------------------------------------------------------------------------------------------------------------

// Função para mover e zipar arquivos de todos os dias anteriores
function processPreviousDayFiles() {
    console.log('Iniciando processPreviousDayFiles...');
    const currentDate = new Date();
    const currentDateStr = currentDate.toISOString().split("T")[0]; // Formato YYYY-MM-DD
    console.log(`Data atual: ${currentDateStr}`);

    // Diretório raiz dos logs, excluindo pastas temporárias
    const equipamentos = fs.readdirSync(logsDir).filter(file => {
        const filePath = path.join(logsDir, file);
        return fs.statSync(filePath).isDirectory() && !file.startsWith('temp-');
    });
    console.log(`Equipamentos encontrados: ${equipamentos.length > 0 ? equipamentos.join(', ') : 'Nenhum'}`);

    equipamentos.forEach(equipamentoId => {
        const equipamentoDir = path.join(logsDir, equipamentoId);
        const dateDirs = fs.readdirSync(equipamentoDir).filter(dir => {
            const dirPath = path.join(equipamentoDir, dir);
            return fs.statSync(dirPath).isDirectory() && dir < currentDateStr; // Apenas dias anteriores
        });
        console.log(`Dias anteriores encontrados para ${equipamentoId}: ${dateDirs.length > 0 ? dateDirs.join(', ') : 'Nenhum'}`);

        dateDirs.forEach(previousDateStr => {
            const previousDayDir = path.join(equipamentoDir, previousDateStr);
            console.log(`Verificando diretório: ${previousDayDir}`);

            // Verifica se o diretório existe
            if (fs.existsSync(previousDayDir)) {
                console.log(`Diretório ${previousDayDir} existe, processando...`);
                const tempDir = path.join(logsDir, `temp-${previousDateStr}`);

                // Cria diretório temporário
                if (!fs.existsSync(tempDir)) {
                    fs.mkdirSync(tempDir, { recursive: true });
                    console.log(`Diretório temporário criado: ${tempDir}`);
                }

                // Move arquivos para o diretório temporário
                const files = fs.readdirSync(previousDayDir);
                console.log(`Arquivos encontrados em ${previousDayDir}: ${files.length > 0 ? files.join(', ') : 'Nenhum'}`);

                files.forEach(file => {
                    const oldPath = path.join(previousDayDir, file);
                    const newPath = path.join(tempDir, file);
                    try {
                        fs.renameSync(oldPath, newPath);
                        console.log(`Arquivo movido: ${oldPath} -> ${newPath}`);
                    } catch (err) {
                        console.error(`Erro ao mover arquivo ${oldPath}:`, err);
                    }
                });

                // Zipa arquivos e salva na pasta logfiles, se houver arquivos
                if (files.length > 0) {
                    const outputZipPath = path.join(logFilesDir, `${equipamentoId}-${previousDateStr}.zip`);
                    console.log(`Criando ZIP em: ${outputZipPath}`);
                    const output = fs.createWriteStream(outputZipPath);
                    const archive = archiver('zip', { zlib: { level: 9 } });

                    output.on('close', () => {
                        console.log(`ZIP concluído: ${outputZipPath}, tamanho: ${archive.pointer()} bytes`);
                        // Remove o diretório temporário e o diretório do dia anterior após zipar
                        try {
                            fs.rmSync(tempDir, { recursive: true, force: true });
                            console.log(`Diretório temporário ${tempDir} removido`);
                            fs.rmSync(previousDayDir, { recursive: true, force: true });
                            console.log(`Diretório do dia anterior ${previousDayDir} removido`);
                        } catch (err) {
                            console.error(`Erro ao remover diretórios:`, err);
                        }
                    });

                    archive.on('error', (err) => {
                        console.error('Erro ao zipar arquivos:', err);
                    });

                    archive.pipe(output);
                    archive.directory(tempDir, false);
                    archive.finalize();
                } else {
                    console.log('Nenhum arquivo para processar, removendo diretórios...');
                    // Remove os diretórios mesmo sem arquivos
                    try {
                        fs.rmSync(tempDir, { recursive: true, force: true });
                        console.log(`Diretório temporário ${tempDir} removido`);
                        fs.rmSync(previousDayDir, { recursive: true, force: true });
                        console.log(`Diretório do dia anterior ${previousDayDir} removido`);
                    } catch (err) {
                        console.error(`Erro ao remover diretórios:`, err);
                    }
                }
            } else {
                console.log(`Diretório ${previousDayDir} não existe, pulando...`);
            }
        });
    });

    // Limpeza de pastas temporárias antigas
    const tempDirs = fs.readdirSync(logsDir).filter(file => file.startsWith('temp-'));
    tempDirs.forEach(tempDir => {
        const tempDirPath = path.join(logsDir, tempDir);
        console.log(`Verificando pasta temporária antiga: ${tempDirPath}`);
        try {
            fs.rmSync(tempDirPath, { recursive: true, force: true });
            console.log(`Pasta temporária antiga ${tempDirPath} removida`);
        } catch (err) {
            console.error(`Erro ao remover pasta temporária antiga ${tempDirPath}:`, err);
        }
    });
}

// Agendamento com node-cron para rodar a cada 1 hora
cron.schedule('0 */1 * * *', () => {
    console.log('Tarefa do node-cron iniciada em:', new Date().toISOString());
    processPreviousDayFiles();
}, {
    scheduled: true,
    timezone: "America/Sao_Paulo"
});

// ---------------------------------------------------------------------------------------------------------------------------------------

// Rota /leituras
app.post("/leituras", async (req, res) => {
    try {
        const leituras = req.body;
        const timestamp = new Date(new Date().getTime() - 3 * 60 * 60 * 1000).toISOString().replace(/[:.]/g, "-");
        const equipamentoId = req.query.id;
        const currentDate = new Date().toISOString().split("T")[0];
        const equipamentoDir = path.join(logsDir, equipamentoId, currentDate);

        if (!fs.existsSync(equipamentoDir)) fs.mkdirSync(equipamentoDir, { recursive: true });

        // Salvar JSON como log
        const logFile = path.join(equipamentoDir, `leituras-${timestamp}.json`);
        fs.writeFileSync(logFile, JSON.stringify(leituras, null, 2));

        let totalOcupacao = 0;
        const ocupacaoPorTimestamp = {};

        // Processar leituras e calcular ocupação e contagem de "1"s
        for (const leitura of leituras) {
            const totalLeituras = leitura.leituras.length;
            const leituras1 = leitura.leituras.filter(l => l === "1").length;
            const leituras0 = totalLeituras - leituras1;
            const ocupacao = leitura.largura * (leituras1 / totalLeituras);

            totalOcupacao += ocupacao;

            // Inicializa o Map com um objeto vazio se o timestamp ainda não existir
            if (!ocupacaoPorTimestamp[leitura.timestamp]) {
                ocupacaoPorTimestamp[leitura.timestamp] = {
                    ocupacoes: [],
                    total1s: 0
                };
            }

            // Contar as leituras "1" para cada leitura individual
            ocupacaoPorTimestamp[leitura.timestamp].ocupacoes.push({
                timestamp: leitura.timestamp,
                ocupacao,
                percentual1: (leituras1 / totalLeituras) * 100,
                percentual0: (leituras0 / totalLeituras) * 100,
            });
            // Atualizar o contador total de "1"s para o timestamp
            ocupacaoPorTimestamp[leitura.timestamp].total1s += leituras1;
        }

        // Exibindo as ocupações de forma mais legível
        console.log(JSON.stringify(ocupacaoPorTimestamp, null, 2));

        let total_occupied_percentage = 0;

        // Agregar os dados para calcular a média de ocupação e quantidade de "1"s
        const ocupacaoMediaPorTimestamp = Object.entries(ocupacaoPorTimestamp).map(([timestamp, { ocupacoes, total1s }]) => {
            const totalOcupacao = ocupacoes.reduce((acc, curr) => acc + curr.ocupacao, 0);
            const mediaOcupacao = ocupacoes.length > 0 ? totalOcupacao / ocupacoes.length : 0;
            const totalLeiturasEsperadas = ocupacoes.length * 44;
            const percentage_occupied = totalLeiturasEsperadas > 0 ? (total1s * 100) / totalLeiturasEsperadas : 0;
            total_occupied_percentage += percentage_occupied;

            // Converter o timestamp para o formato ISO
            const [date, time] = timestamp.split('_');
            const [year, month, day] = date.split('.');
            const [hour, minute, second] = time.split('.');  
            const isoTimestamp = new Date(Date.UTC(year, month - 1, day, hour, minute, second)).toISOString();

            return {
                LinhaPinturaUtilizacaoEquipId: equipamentoId,
                LinhaPinturaUtilizacaoDtHr: isoTimestamp,
                LinhaPinturaUtilizacaoPerOcup: Number(percentage_occupied.toFixed(2)),
                LinhaPinturaUtilizacaoParada: percentage_occupied === 0,
                LinhaPinturaUtilizacaoQtdeSensores: 44,
            };
        });

        console.log('Ocupação média por timestamp:', ocupacaoMediaPorTimestamp);
        console.log('Total percentual de ocupação acumulado:', total_occupied_percentage);

        // Enviar os dados para a API
        const data = { linhapudata: ocupacaoMediaPorTimestamp };
        console.log(data);

        try {
            const response = await axios.post(`${process.env.PRODUX_BASEURL}/Api/data/setLinhaPinturaUtilizacao`, data, {
                headers: { 'Token': process.env.PRODUX_TOKEN }
            });

            console.log("Resposta da API:", response.data);
            // Resposta após a requisição à API
            res.status(200).json({ success: true, data: response.data, total_occupied_percentage });
        } catch (error) {
            console.error("Erro ao processar leituras:", error);
            // Resposta em caso de erro na requisição à API
            res.status(500).json({ error: "Erro interno ao processar os dados" });
        }
    } catch (error) {
        console.error("Erro ao processar leituras:", error);
        // Resposta geral de erro
        res.status(500).json({ error: "Erro interno ao processar os dados" });
    }
});

// ---------------------------------------------------------------------------------------------------------------------------------------

app.listen(PORT, () => console.log(`API rodando em http://localhost:${PORT}`));