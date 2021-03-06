#!/usr/bin/env python
#coding=utf-8

from __future__ import division

import os
import sys
import argparse
import time
import shutil
import pdb

import tensorflow as tf
from tensorflow.python.client import timeline

from seq2seq_model import Seq2SeqModel
from utils import get_available_gpus, add_arguments, create_hparams

SINGLE_CARD_SPEED = None
WARM_UP_BATCH = 10


def make_config():
    config = tf.ConfigProto()

    config.log_device_placement = False
    config.gpu_options.allow_growth = True
    config.allow_soft_placement = True

    config.intra_op_parallelism_threads = 0
    config.inter_op_parallelism_threads = 56

    return config


def profiling_train(model, config, hparams):

    builder = tf.profiler.ProfileOptionBuilder
    opts = builder(builder.time_and_memory()).order_by("micros").build()

    tf.profiler.profile(
        tf.get_default_graph(),
        options=tf.profiler.ProfileOptionBuilder.float_operation())

    options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
    run_metadata = tf.RunMetadata()
    with tf.contrib.tfprof.ProfileContext(
            os.path.join("timeline_info", "%02d_cards" % (model.num_gpus)),
            trace_steps=[],
            dump_steps=[]) as pctx:

        sv = tf.train.Supervisor(
            is_chief=True,
            logdir="train_log",
            ready_for_local_init_op=None,
            local_init_op=model.local_var_init_op_group,
            saver=model.saver,
            global_step=model.global_step,
            summary_op=None,
            save_model_secs=600,
            summary_writer=None)
        with sv.managed_session(
                master="", config=config,
                start_standard_services=False) as sess:

            pass_id = 0
            batch_id = 0

            start_time = time.time()
            total_word_count = 0

            if not hparams.use_synthetic_data:
                sess.run(model.iterator.initializer)

            while True:
                try:
                    if batch_id == 4:
                        pctx.trace_next_step()
                        pctx.dump_next_step()

                    _, loss, word_count = sess.run(
                        list(model.fetches.values()) + [model.word_count],
                        options=options,
                        run_metadata=run_metadata)

                    total_word_count += word_count
                    pctx.profiler.profile_operations(options=opts)

                    print("Pass %d, Batch %d, Loss : %.5f" % (pass_id,
                                                              batch_id, loss))
                    batch_id += 1
                    print("batch_id = %d" % batch_id)
                    if batch_id == 5:
                        fetched_timeline = timeline.Timeline(
                            run_metadata.step_stats)
                        chrome_trace = \
                                fetched_timeline.generate_chrome_trace_format()
                        with open("timeline_info/%02d_cards.json" %
                                  (model.num_gpus), "w") as f:
                            f.write(chrome_trace)
                        return

                except tf.errors.OutOfRangeError:
                    if not hparams.use_synthetic_data:
                        sess.run(iterator.initializer)
                    batch_id = 0
                    continue


def train(model, config, hparams):
    sv = tf.train.Supervisor(
        is_chief=True,
        logdir="train_log",
        ready_for_local_init_op=None,
        local_init_op=model.local_var_init_op_group,
        saver=model.saver,
        global_step=model.global_step,
        summary_op=None,
        save_model_secs=600,
        summary_writer=None)
    with sv.managed_session(
            master="", config=config, start_standard_services=False) as sess:

        tb_log_dir = "tblog"
        if os.path.exists(tb_log_dir): shutil.rmtree(tb_log_dir)
        else: os.mkdir(tb_log_dir)
        writer = tf.summary.FileWriter(tb_log_dir, sess.graph)

        pass_id = 0
        batch_id = 0

        total_word_count = 0
        start_time = None

        if not hparams.use_synthetic_data:
            sess.run(model.iterator.initializer)

        while True:
            try:
                _, loss, word_count = sess.run(
                    list(model.fetches.values()) + [model.word_count])

                if batch_id == WARM_UP_BATCH:
                    start_time = time.time()
                total_word_count += (word_count
                                     if batch_id >= WARM_UP_BATCH else 0)

                if batch_id and not batch_id % 5:
                    print("Pass %d, Batch %d, Loss : %.5f" % (pass_id,
                                                              batch_id, loss))
                batch_id += 1

                if batch_id == 30:
                    print("Pass %d, Batch %d, Loss : %.5f" % (pass_id,
                                                              batch_id, loss))
                    time_elapsed = time.time() - start_time
                    speed = total_word_count / time_elapsed
                    ratio = (1. if SINGLE_CARD_SPEED is None else
                             speed / SINGLE_CARD_SPEED)

                    print(("|gpu number|batch_size|total time|"
                           "speed|speedup ratio|\n"
                           "|%d|%d|%.3f|%.3f|%.2f|") %
                          (model.num_gpus, hparams.batch_size, time_elapsed,
                           speed, ratio))
                    break

            except tf.errors.OutOfRangeError:
                if not hparams.use_synthetic_data:
                    sess.run(model.iterator.initializer)
                batch_id = 0
                continue


def main(unused_argv):
    hparams = create_hparams(FLAGS)
    model = Seq2SeqModel(hparams)

    print("num_gpus = %d, batch size = %d" %
          (model.num_gpus, hparams.batch_size * model.num_gpus))
    config = make_config()

    if hparams.enable_profile:
        profiling_train(model, config, hparams),
    else:
        train(model, config, hparams)


if __name__ == "__main__":
    param_parser = argparse.ArgumentParser()
    add_arguments(param_parser)
    FLAGS, unparsed = param_parser.parse_known_args()
    tf.app.run(main=main, argv=[sys.argv[0]] + unparsed)
