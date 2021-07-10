# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for deepconsensus.models.data_providers."""

from absl.testing import absltest
from absl.testing import parameterized
import numpy as np
import tensorflow as tf

from deepconsensus.models import data_providers
from deepconsensus.models import model_configs
from deepconsensus.models import model_utils
from deepconsensus.protos import deepconsensus_pb2
from deepconsensus.tf_examples import tf_example_utils
from deepconsensus.utils import dc_constants
from deepconsensus.utils import test_utils


class DataProvidersTest(parameterized.TestCase):

  @parameterized.named_parameters(
      dict(
          testcase_name='batch size evenly divides # examples',
          num_epochs=1,
          batch_size=1,
      ),
      dict(
          testcase_name='multiple epochs',
          num_epochs=5,
          batch_size=1,
      ),
      dict(
          testcase_name='batch size does not evenly divide # examples',
          num_epochs=5,
          batch_size=10,
      ),
  )
  def test_get_dataset(self, num_epochs, batch_size):
    """Checks that batches are of expected size and all examples yielded."""

    # Dataset sizes computed using gqui. Currently, eval set is empty because
    # the testdata only contains one molecule, which is added to training set
    # based on end position.
    # <internal>
    dataset = 'train'
    dataset_size = 253
    file_pattern = test_utils.deepconsensus_testdata(
        'ecoli/output/tf_examples/%s/*.tfrecords.gz' % dataset)
    params = model_configs.get_config('transformer+test')
    model_utils.modify_params(params)
    dataset = data_providers.get_dataset(
        file_pattern=file_pattern,
        num_epochs=num_epochs,
        batch_size=batch_size,
        params=params,
        drop_remainder=False)
    total = 0
    for subreads, label in dataset.as_numpy_iterator():
      # Last batch may contain fewer examples.
      self.assertLen(subreads, len(label))
      self.assertLessEqual(len(subreads), batch_size)
      total += len(subreads)
    self.assertEqual(total, num_epochs * dataset_size)

  @parameterized.named_parameters(
      dict(
          testcase_name='batch size evenly divides # examples',
          num_epochs=1,
          batch_size=1,
      ),
      dict(
          testcase_name='multiple epochs',
          num_epochs=5,
          batch_size=1,
      ),
      dict(
          testcase_name='batch size does not evenly divide # examples',
          num_epochs=5,
          batch_size=10,
      ),
  )
  def test_get_dataset_with_metadata(self, num_epochs, batch_size):
    """Checks that batches are of expected size and all examples yielded."""

    # Dataset sizes computed using gqui. Currently, eval set is empty because
    # the testdata only contains one molecule, which is added to training set
    # based on end position.
    # <internal>
    dataset = 'train'
    dataset_size = 253
    file_pattern = test_utils.deepconsensus_testdata(
        'ecoli/output/tf_examples/%s/*.tfrecords.gz' % dataset)
    params = model_configs.get_config('transformer+test')
    model_utils.modify_params(params)
    dataset = data_providers.get_dataset_with_metadata(
        file_pattern=file_pattern,
        num_epochs=num_epochs,
        batch_size=batch_size,
        params=params,
        drop_remainder=False)
    total = 0
    for subreads, label, num_passes, encoded_deepconsensus_input in dataset.as_numpy_iterator(
    ):
      # Last batch may contain fewer examples.
      self.assertLen(subreads, len(label))
      self.assertLessEqual(len(subreads), batch_size)
      # Sanity check the values in the num_passes array.
      self.assertTrue(tf.reduce_all(num_passes <= 20))
      self.assertTrue(tf.reduce_all(num_passes > 0))
      total += len(subreads)

      # Sanity check that DeepConsensusInput protos can be parsed correctly.
      for i in range(len(encoded_deepconsensus_input)):
        curr_deepconsensus_input = deepconsensus_pb2.DeepConsensusInput.FromString(
            encoded_deepconsensus_input[i])
        curr_num_passes = num_passes[i]
        self.assertLessEqual(curr_num_passes,
                             len(curr_deepconsensus_input.subreads))
        self.assertNotEmpty(curr_deepconsensus_input.subreads)
    self.assertEqual(total, num_epochs * dataset_size)

  @parameterized.named_parameters(
      dict(
          testcase_name='batch size evenly divides # examples',
          num_epochs=1,
          batch_size=1,
      ),)
  def test_get_dataset_with_pw_ip(self, num_epochs, batch_size):
    """Checks that batches are of expected size and all examples yielded."""

    dataset = 'train'
    file_pattern = test_utils.deepconsensus_testdata(
        'ecoli/output/tf_examples/%s/*.tfrecords.gz' % dataset)
    params = model_configs.get_config('transformer_learn_values+test')
    model_utils.modify_params(params)
    dataset = data_providers.get_dataset(
        file_pattern=file_pattern,
        num_epochs=num_epochs,
        batch_size=batch_size,
        params=params,
    )
    check_not_empty = False
    for subreads, _ in dataset.as_numpy_iterator():
      check_not_empty = True
      base_indices, pw_indices, ip_indices, strand_indices, ccs_indices, sn_indices = tf_example_utils.get_indices(
          params.max_passes)
      base_rows = subreads[:, slice(*base_indices), :, :]
      pw_rows = subreads[:, slice(*pw_indices), :, :]
      ip_rows = subreads[:, slice(*ip_indices), :, :]
      strand_rows = subreads[:, slice(*strand_indices), :, :]
      ccs_rows = subreads[:, slice(*ccs_indices), :, :]
      sn_rows = subreads[:, slice(*sn_indices), :, :]
      self.assertNotEmpty(base_rows)
      self.assertNotEmpty(pw_rows)
      self.assertNotEmpty(ip_rows)
      self.assertNotEmpty(strand_rows)
      self.assertNotEmpty(ccs_rows)
      self.assertNotEmpty(sn_rows)
      self.assertTrue(np.all(base_rows < params.vocab_size))
      self.assertTrue(np.all(ip_rows <= dc_constants.IP_MAX))
      self.assertTrue(np.all(pw_rows <= dc_constants.PW_MAX))
    self.assertTrue(check_not_empty)  # Used to fail on empty dataset.

  @parameterized.named_parameters(
      dict(
          testcase_name='limit number of examples',
          limit=42,
      ),
      dict(
          testcase_name='limit set to size greater than dataset',
          limit=int(1e6)),
  )
  def test_dataset_with_limit_option(self, limit):
    """Checks that batches are of expected size and all examples yielded."""

    dataset = 'train'
    file_pattern = test_utils.deepconsensus_testdata(
        'ecoli/output/tf_examples/%s/*.tfrecords.gz' % dataset)
    params = model_configs.get_config('transformer_learn_values+test')
    model_utils.modify_params(params)
    # Fetch the complete dataset.
    full_dataset = data_providers.get_dataset(
        file_pattern=file_pattern,
        num_epochs=1,
        batch_size=1,
        params=params,
    )
    full_dataset_size = sum(1 for record in full_dataset)

    # Fetch dataset with the limit flag.
    dataset = data_providers.get_dataset(
        file_pattern=file_pattern,
        num_epochs=1,
        batch_size=1,
        params=params,
        limit=limit)
    limit_dataset_size = sum(1 for record in dataset)
    self.assertEqual(min(limit, full_dataset_size), limit_dataset_size)

  def test_remove_internal_gaps_and_shift(self):
    label, expected = ('   GGGCGAG   ACATA   ACATA ATA ATA      ',
                       'GGGCGAGACATAACATAATAATA                 ')
    label = [float(dc_constants.VOCAB.index(x)) for x in label]
    label = tf.expand_dims(tf.constant(label), axis=0)
    shifted = data_providers.remove_internal_gaps_and_shift(label)
    result = ''.join([dc_constants.VOCAB[int(x)] for x in shifted])
    self.assertEqual(result, expected)


if __name__ == '__main__':
  absltest.main()