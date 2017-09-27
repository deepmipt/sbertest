import os
import json
import requests

from deeppavlov.agents.insults.insults_agents import EnsembleInsultsAgent


class tester():

    def __init__(self, config, opt):
        self.config = config
        self.opt = opt
        self.kpi_name = config['kpi_name']
        self.session_id = None
        self.numtasks = None
        self.tasks = None
        self.observations = None
        self.agent_params = None
        self.predictions = None
        self.answers = None
        self.score = None

    # Get kpi1 tasks via REST
    def get_tasks(self):
        get_url = self.config['kpis'][self.kpi_name]['settings_kpi']['rest_url']
        test_tasks_number = self.config['kpis'][self.kpi_name]['settings_kpi']['test_tasks_number']
        get_params = {'stage': 'test', 'quantity': test_tasks_number}
        get_response = requests.get(get_url, params=get_params)
        tasks = json.loads(get_response.text)
        return tasks

    # Prepare observations set
    def make_observations(self, tasks):
        observations = []
        for task in tasks['qas']:
            observations.append({
                'id': task['id'],
                'text': task['question'],
            })
        return observations

    # Generate params for EnsembleParaphraserAgent
    def make_agent_params(self):
        embeddings_dir = self.config['embeddings_dir']
        embedding_file = self.config['kpis'][self.kpi_name]['settings_agent']['fasttext_model']
        model_files = self.opt['model_files']
        agent_params = {
            'model_files': model_files,
            'model_names': self.config['kpis'][self.kpi_name]['settings_agent']['model_names'],
            'model_coefs': self.config['kpis'][self.kpi_name]['settings_agent']['model_coefs'],
            'datatype': 'test',
            'kernel_sizes_cnn': self.config['kpis'][self.kpi_name]['settings_agent']['kernel_sizes_cnn'],
            'pool_sizes_cnn': self.config['kpis'][self.kpi_name]['settings_agent']['pool_sizes_cnn'],
            'fasttext_model': os.path.join(embeddings_dir, embedding_file)
        }
        return agent_params

    # Process observations via algorithm
    def get_predictions(self, opt, observations):
        agent = EnsembleInsultsAgent(opt)
        predictions = agent.batch_act(observations)
        return predictions

    # Generate answers data
    def make_answers(self, session_id, observations, predictions):
        answers = {}
        answers['sessionId'] = session_id
        answers['answers'] = {}
        observ_predict = list(zip(observations, predictions))
        for obs, pred in observ_predict:
            answers['answers'][obs['id']] = pred['score']
        return answers

    # Post answers data and get score
    def get_score(self, answers):
        post_headers = {'Accept': '*/*'}
        rest_response = requests.post(self.config['kpis'][self.kpi_name]['settings_kpi']['rest_url'], \
                                      json=answers, \
                                      headers=post_headers)
        return rest_response.text

    # Run full cycle of testing session and store data for each step
    def run_test(self):
        tasks = self.get_tasks()
        session_id = tasks['id']
        numtasks = tasks['total']
        self.tasks = tasks
        self.session_id = session_id
        self.numtasks = numtasks

        observations = self.make_observations(tasks)
        self.observations = observations

        agent_params = self.make_agent_params()
        self.agent_params = agent_params

        predictions = self.get_predictions(agent_params, observations)
        self.predictions = predictions

        answers = self.make_answers(session_id, observations, predictions)
        self.answers = answers

        score = self.get_score(answers)
        self.score = score