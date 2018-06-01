#!/usr/bin/env python
#coding=utf-8
#!/usr/bin/env python
#coding=utf-8
import pdb
import time

import tensorflow as tf
from tensorflow.python.client import timeline

from iterator_helper import get_iterator
from seq2seq_model import Seq2SeqModel, hparams

from utils import get_available_gpus
from timeline_utils import TimeLiner


def make_config():
    config = tf.ConfigProto()

    config.log_device_placement = False
    config.gpu_options.allow_growth = True
    config.allow_soft_placement = True

    config.intra_op_parallelism_threads = 0
    config.inter_op_parallelism_threads = 0
    return config


def train():
    num_gpus = len(get_available_gpus())
    print("num_gpus = %d, batch size = %d" % (num_gpus,
                                              hparams.batch_size * num_gpus))

    model = Seq2SeqModel(num_gpus, hparams)

    config = make_config()

    # for profiling
    builder = tf.profiler.ProfileOptionBuilder
    opts = builder(builder.time_and_memory()).order_by("micros").build()

    # for TF timeline
    options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
    run_metadata = tf.RunMetadata()
    many_runs_timeline = TimeLiner()

    with tf.contrib.tfprof.ProfileContext(
            "profiling_%02d_cards" % (num_gpus), trace_steps=[],
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

            sess.run(model.iterator.initializer)

            while True:
                try:
                    if batch_id == 2:
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
                    if batch_id == 3: break

                except tf.errors.OutOfRangeError:
                    sess.run(iterator.initializer)
                    batch_id = 0
                    continue


if __name__ == "__main__":
    train()