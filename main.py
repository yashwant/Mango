"""
This module runs TensorFlow instances to train and evaluate the model.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
import os
import datetime
import tensorflow as tf

from model.model import model_fn
from model.dataset import Data

tf.reset_default_graph()
tf.logging.set_verbosity(tf.logging.INFO)

FLAGS = tf.app.flags.FLAGS

tf.app.flags.DEFINE_integer('seed', 67, 'Random seed.')
tf.app.flags.DEFINE_string('dataset_path', 'datasets/processed/qa1_single-supporting-fact_1k.json', 'Dataset path.')
tf.app.flags.DEFINE_string('model_dir', 'logs/', 'Model directory.')
tf.app.flags.DEFINE_integer('examples_per_epoch', 1000, 'Number of examples per epoch.')
tf.app.flags.DEFINE_integer('batch_size', 40, 'Batch size.')
tf.app.flags.DEFINE_integer('num_epochs', 500, 'Number of training epochs.')
tf.app.flags.DEFINE_integer('embedding_size', 100, 'Embedding size.')
tf.app.flags.DEFINE_integer('hidden_size', 500, 'GRU hidden size.')
tf.app.flags.DEFINE_float('learning_rate', 5e-3, 'Base learning rate.')
tf.app.flags.DEFINE_float('clip_gradients', 40.0, 'Clip the global norm of the gradients to this value.')
tf.app.flags.DEFINE_integer('early_stopping_rounds', 100, 'Number of epochs before early stopping.')
tf.app.flags.DEFINE_boolean('debug', False, 'Debug mode to enable more summaries and numerical checks.')


def main(_):

    dataset = Data(FLAGS.dataset_path, FLAGS.batch_size, FLAGS.examples_per_epoch)
    train_input_fn = dataset.get_input_fn('train', num_epochs=FLAGS.num_epochs, shuffle=True)
    eval_input_fn = dataset.get_input_fn('test', num_epochs=1, shuffle=False)

    params = {
        'vocab_size_char': dataset.vocab_size_char,
        'vocab_size_word': dataset.vocab_size_word,
        'max_story_length': dataset.max_story_length,
        'max_story_char_length': dataset.max_story_char_length,
        'max_story_word_length': dataset.max_story_word_length,
        'embedding_size': FLAGS.embedding_size,
        'batch_size_int': FLAGS.batch_size,
        'hidden_size': FLAGS.hidden_size,
        'token_space': dataset.tokens_char[' '],
        'token_sentence': dataset.tokens_char['.'],
        'learning_rate_init': FLAGS.learning_rate,
        'learning_rate_decay_steps': 1200,
        'learning_rate_decay_rate': 0.5,
        'clip_gradients': FLAGS.clip_gradients,
        'debug': FLAGS.debug,
    }

    config = tf.contrib.learn.RunConfig(
        tf_random_seed=FLAGS.seed,
        save_summary_steps=120,
        save_checkpoints_secs=120,
        keep_checkpoint_max=5,
        keep_checkpoint_every_n_hours=1,
        log_device_placement=True)

    dataset_name = os.path.splitext(os.path.basename(FLAGS.dataset_path))[0]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    model_dir = os.path.join(FLAGS.model_dir, dataset_name, str(timestamp))

    estimator = tf.contrib.learn.Estimator(
        model_dir=model_dir,
        model_fn=model_fn,
        config=config,
        params=params)

    validation_metrics = {
        "accuracy": tf.contrib.learn.metric_spec.MetricSpec(tf.contrib.metrics.streaming_accuracy)
    }

    validation_monitors = [tf.contrib.learn.monitors.ValidationMonitor(
        input_fn=eval_input_fn,
        early_stopping_rounds=FLAGS.early_stopping_rounds * dataset.steps_per_epoch,
        early_stopping_metric='loss',
        early_stopping_metric_minimize=True
    )]

    experiment = tf.contrib.learn.Experiment(
        estimator,
        train_input_fn,
        eval_input_fn,
        train_steps=None,
        eval_steps=None,
        eval_metrics=validation_metrics,
        train_monitors=validation_monitors,
        local_eval_frequency=1)

    experiment.train_and_evaluate()

if __name__ == '__main__':
    tf.app.run()
